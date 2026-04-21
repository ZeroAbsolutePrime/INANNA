# CURRENT PHASE: Cycle 7 - Phase 7.5 - The Voice Listener
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Cycle: 7 - NYXOS: The Sovereign Intelligence Operating System**
**Replaces: Cycle 7 Phase 7.4 - The Package Faculty (COMPLETE)**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — implement voice listener service
TESTER:     Codex — unit tests (no microphone required)
VERIFIER:   Command Center — confirm after push

BUILDER forbidden from:
  - Modifying any existing faculty files
  - Changing web UI (index.html, console.html)
  - Implementing TTS output (Phase 7.6)

---

## What This Phase Is

Phases 7.1-7.4 gave INANNA hands and eyes — file system, processes,
packages.
Phase 7.5 gives INANNA ears.

The Voice Listener is a standalone Python process that:
1. Listens to the microphone continuously
2. Uses Silero VAD to detect when someone is speaking
3. When speech ends, passes the audio to faster-whisper
4. Sends the transcribed text to INANNA via WebSocket
5. INANNA receives it as if the user had typed it

The result: you speak, INANNA hears, INANNA responds.
Phase 7.6 will add the voice output (INANNA speaks back).
Phase 7.7 will close the loop completely.

This phase is a SEPARATE PROCESS — not part of the INANNA server.
You run it alongside the server.
It communicates via the existing WebSocket on port 8081.

---

## Technology Stack

faster-whisper: 4x faster than openai-whisper, no FFmpeg needed,
  runs on CPU, excellent multilingual support (es/en/pt).
  Model: base (145MB) for low latency, small (244MB) for accuracy.

sounddevice: cross-platform microphone access via Python.
  Works on Windows, Linux, macOS.

silero-vad: lightweight Voice Activity Detection.
  Detects when speech starts and stops.
  Prevents sending silence to Whisper.
  Runs on CPU, very fast (~1ms per frame).

---

## What You Are Building

### Task 1 - inanna/voice/listener.py

Create directory: inanna/voice/
Create: inanna/voice/__init__.py (empty)
Create: inanna/voice/listener.py

```python
"""
INANNA NYX Voice Listener
Microphone → VAD → faster-whisper → WebSocket → INANNA

Run standalone:
  python -m voice.listener [--model base] [--lang es] [--ws ws://localhost:8081]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import queue
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

log = logging.getLogger("inanna.voice")

# Sample rate required by Whisper and Silero VAD
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"
# VAD chunk size: 512 samples = 32ms at 16kHz
VAD_CHUNK = 512
# Silence threshold: stop recording after this many seconds of silence
SILENCE_TIMEOUT = 1.2
# Minimum speech duration to send to Whisper
MIN_SPEECH_SECONDS = 0.5


class VoiceListener:
    """
    Listens to the microphone, detects speech with Silero VAD,
    transcribes with faster-whisper, sends to INANNA via WebSocket.
    """

    def __init__(
        self,
        model_size: str = "base",
        language: Optional[str] = None,
        ws_url: str = "ws://localhost:8081",
        device: str = "cpu",
    ) -> None:
        self.model_size = model_size
        self.language = language  # None = auto-detect
        self.ws_url = ws_url
        self.device = device
        self._audio_queue: queue.Queue = queue.Queue()
        self._whisper = None
        self._vad_model = None
        self._vad_utils = None

    def _load_whisper(self) -> None:
        log.info("Loading faster-whisper model: %s", self.model_size)
        from faster_whisper import WhisperModel
        self._whisper = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type="int8" if self.device == "cpu" else "float16",
        )
        log.info("Whisper model loaded.")

    def _load_vad(self) -> None:
        log.info("Loading Silero VAD...")
        import torch
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
        self._vad_model = model
        self._vad_utils = utils
        log.info("Silero VAD loaded.")

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio array (float32, 16kHz) to text."""
        if self._whisper is None:
            self._load_whisper()
        segments, _info = self._whisper.transcribe(
            audio_data,
            language=self.language,
            beam_size=3,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text

    def _is_speech(self, chunk: np.ndarray) -> float:
        """Returns speech probability for an audio chunk (0.0-1.0)."""
        import torch
        tensor = torch.from_numpy(chunk).float()
        return float(self._vad_model(tensor, SAMPLE_RATE).item())

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info,
        status,
    ) -> None:
        """Called by sounddevice for each audio block."""
        self._audio_queue.put(indata.copy().flatten())

    def _collect_speech(self) -> Optional[np.ndarray]:
        """
        Reads from the audio queue, uses VAD to detect speech start/end.
        Returns a numpy array of speech audio, or None if timed out.
        """
        if self._vad_model is None:
            self._load_vad()

        speech_frames = []
        in_speech = False
        silence_start = None
        SPEECH_THRESHOLD = 0.5
        SILENCE_THRESHOLD = 0.3

        while True:
            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                if in_speech and silence_start:
                    elapsed = time.time() - silence_start
                    if elapsed > SILENCE_TIMEOUT:
                        break
                continue

            prob = self._is_speech(chunk)

            if prob >= SPEECH_THRESHOLD:
                if not in_speech:
                    in_speech = True
                    log.debug("Speech detected (prob=%.2f)", prob)
                silence_start = None
                speech_frames.append(chunk)
            elif in_speech:
                speech_frames.append(chunk)
                if prob < SILENCE_THRESHOLD:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > SILENCE_TIMEOUT:
                        break

        if not speech_frames:
            return None

        audio = np.concatenate(speech_frames)
        duration = len(audio) / SAMPLE_RATE
        if duration < MIN_SPEECH_SECONDS:
            log.debug("Audio too short (%.2fs), skipping.", duration)
            return None

        return audio

    async def run(self) -> None:
        """Main loop: listen, transcribe, send to INANNA."""
        import sounddevice as sd
        import websockets

        self._load_whisper()
        self._load_vad()

        print("𒀭 INANNA Voice Listener active.")
        print(f"   Model:    {self.model_size}")
        print(f"   Language: {self.language or 'auto'}")
        print(f"   Server:   {self.ws_url}")
        print("   Listening... Speak to INANNA. Press Ctrl+C to stop.")
        print()

        ws_conn = None

        async def get_ws():
            nonlocal ws_conn
            try:
                if ws_conn is None or ws_conn.closed:
                    ws_conn = await websockets.connect(self.ws_url)
                return ws_conn
            except Exception as e:
                log.warning("WebSocket reconnect failed: %s", e)
                ws_conn = None
                return None

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=VAD_CHUNK,
            callback=self._audio_callback,
        ):
            while True:
                audio = await asyncio.to_thread(self._collect_speech)
                if audio is None:
                    continue

                log.debug("Transcribing %.2fs of audio...", len(audio)/SAMPLE_RATE)
                t0 = time.time()
                text = await asyncio.to_thread(self.transcribe, audio)
                elapsed = time.time() - t0

                if not text:
                    continue

                print(f"  🎤 [{elapsed:.1f}s] {text}")

                ws = await get_ws()
                if ws:
                    try:
                        await ws.send(json.dumps({
                            "type": "input",
                            "text": text,
                            "source": "voice",
                        }))
                    except Exception as e:
                        log.warning("Failed to send to INANNA: %s", e)
                        ws_conn = None
                else:
                    log.warning("No WebSocket connection — text not sent.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="INANNA NYX Voice Listener"
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Language code: es, en, pt, or None for auto-detect",
    )
    parser.add_argument(
        "--ws",
        default="ws://localhost:8081",
        help="INANNA WebSocket URL",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Inference device (default: cpu)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    listener = VoiceListener(
        model_size=args.model,
        language=args.lang,
        ws_url=args.ws,
        device=args.device,
    )

    try:
        asyncio.run(listener.run())
    except KeyboardInterrupt:
        print("\n𒀭 Voice Listener stopped.")


if __name__ == "__main__":
    main()
```

### Task 2 - inanna/voice/README.md

Create: inanna/voice/README.md

```markdown
# INANNA NYX Voice Listener

Speak to INANNA. She hears you.

## Requirements

Install voice dependencies:

  pip install faster-whisper sounddevice torch

On Windows, sounddevice requires:
  pip install sounddevice
  (PortAudio is bundled)

On NixOS:
  nix-env -iA nixpkgs.portaudio
  pip install sounddevice

## Usage

Start the INANNA server first (port 8081 must be open), then:

  # Auto-detect language, base model
  python -m voice.listener

  # Spanish, small model (more accurate)
  python -m voice.listener --lang es --model small

  # English, with debug output
  python -m voice.listener --lang en --debug

  # Connect to a remote INANNA instance
  python -m voice.listener --ws ws://192.168.1.100:8081

## Models

  tiny   (75MB)   fastest, less accurate
  base   (145MB)  good balance — recommended for CPU
  small  (244MB)  better accuracy, ~2x slower on CPU
  medium (769MB)  high accuracy, needs decent CPU or GPU
  large-v3 (1.5GB) best quality, GPU recommended

## Languages

ZAERA's languages:
  --lang es    Spanish
  --lang en    English
  --lang pt    Portuguese
  (omit for automatic detection)

## How It Works

1. Microphone captures audio at 16kHz
2. Silero VAD detects when you start and stop speaking
3. The speech chunk is sent to faster-whisper
4. The text is sent to INANNA via WebSocket as if you typed it
5. INANNA responds in the conversation

## Latency Budget (CPU, base model)

  VAD detection:        ~30ms
  Whisper transcription: 1-3s (5s speech on CPU)
  Network to INANNA:    ~5ms
  INANNA processing:    2-10s
  Total:                3-13s
```

### Task 3 - Add voice dependencies to requirements.txt

Add to inanna/requirements.txt:
```
# Voice (Phase 7.5 — install separately when using voice)
# faster-whisper>=1.0.0
# sounddevice>=0.4.6
# torch>=2.0.0
```

These are commented out by default because they are large
dependencies not needed for text-only operation.
The voice README explains how to install them.

### Task 4 - Update identity.py

CURRENT_PHASE = "Cycle 7 - Phase 7.5 - The Voice Listener"

### Task 5 - Tests (no microphone required)

Create inanna/tests/test_voice_listener.py:
  - voice/listener.py exists
  - voice/__init__.py exists
  - voice/README.md exists
  - VoiceListener can be instantiated
  - VoiceListener has correct default model_size ("base")
  - VoiceListener has correct default ws_url
  - MIN_SPEECH_SECONDS is 0.5
  - SAMPLE_RATE is 16000
  - VoiceListener.transcribe raises ImportError
    when faster-whisper not installed (graceful)
  - main() argument parser accepts --model, --lang, --ws, --device

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/identity.py
inanna/requirements.txt
inanna/voice/__init__.py        <- NEW (empty)
inanna/voice/listener.py        <- NEW
inanna/voice/README.md          <- NEW
inanna/tests/test_voice_listener.py  <- NEW
inanna/tests/test_identity.py

---

## What You Are NOT Building

- No TTS output (Phase 7.6)
- No voice UI button in index.html (Phase 7.7)
- No changes to server.py or main.py
  (the listener connects as a WebSocket client — no server changes)
- No GPU-specific configuration
- No wake word detection

---

## Definition of Done

- [ ] inanna/voice/ directory with 3 files
- [ ] VoiceListener class with run(), transcribe(), _collect_speech()
- [ ] Voice README documents installation and usage clearly
- [ ] requirements.txt updated with commented voice deps
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## How To Test After Phase 7.5

Install voice dependencies:
  py -3 -m pip install faster-whisper sounddevice torch

Start INANNA server in one terminal:
  cd inanna && py -3 ui_main.py

Start voice listener in another terminal:
  cd inanna && py -3 -m voice.listener --lang es

Speak to INANNA in Spanish or English.
Watch the text appear in the browser interface.

---

## Handoff

Commit: cycle7-phase5-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE7_PHASE5_REPORT.md
Stop. Do not begin Phase 7.6 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-21*
*INANNA gains ears.*
*You speak. She hears. She responds.*
*The keyboard becomes optional.*
*Phase 7.5 is the threshold.*
*Everything before this was preparation.*
*Everything after this is presence.*
