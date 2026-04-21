"""
INANNA NYX Voice Listener
Microphone → VAD → faster-whisper → WebSocket → INANNA

Run standalone:
  python -m voice.listener
  python -m voice.listener --model small --lang es
  python -m voice.listener --ws ws://192.168.1.100:8081

Install dependencies first:
  pip install faster-whisper sounddevice torch
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import queue
import sys
import time
from typing import Optional

log = logging.getLogger("inanna.voice")

# Audio constants
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"
VAD_CHUNK = 512           # 32ms at 16kHz
SILENCE_TIMEOUT = 1.2     # seconds of silence before cut
MIN_SPEECH_SECONDS = 0.5  # ignore clips shorter than this


class VoiceListener:
    """
    Listens to the microphone, detects speech with Silero VAD,
    transcribes with faster-whisper, sends text to INANNA via WebSocket.

    Architecture:
      sounddevice → audio_queue → VAD → speech buffer → Whisper → WebSocket
    """

    def __init__(
        self,
        model_size: str = "base",
        language: Optional[str] = None,
        ws_url: str = "ws://localhost:8081",
        device: str = "cpu",
    ) -> None:
        self.model_size = model_size
        self.language = language
        self.ws_url = ws_url
        self.device = device
        self._audio_queue: queue.Queue = queue.Queue()
        self._whisper = None
        self._vad_model = None

    # ── Model loading ─────────────────────────────────────────────

    def _load_whisper(self) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper not installed. Run: pip install faster-whisper"
            )
        log.info("Loading faster-whisper model: %s on %s", self.model_size, self.device)
        self._whisper = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type="int8" if self.device == "cpu" else "float16",
        )
        log.info("Whisper ready.")

    def _load_vad(self) -> None:
        try:
            import torch
        except ImportError:
            raise ImportError(
                "torch not installed. Run: pip install torch"
            )
        log.info("Loading Silero VAD...")
        model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
        self._vad_model = model
        log.info("VAD ready.")

    # ── Transcription ─────────────────────────────────────────────

    def transcribe(self, audio_data) -> str:
        """Transcribe a numpy float32 16kHz array to text."""
        if self._whisper is None:
            self._load_whisper()
        segments, _info = self._whisper.transcribe(
            audio_data,
            language=self.language,
            beam_size=3,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        return " ".join(seg.text.strip() for seg in segments).strip()

    def _speech_prob(self, chunk) -> float:
        """Returns VAD speech probability for a 512-sample chunk."""
        import torch
        tensor = torch.from_numpy(chunk).float()
        return float(self._vad_model(tensor, SAMPLE_RATE).item())

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        self._audio_queue.put(indata.copy().flatten())

    # ── Speech collection ─────────────────────────────────────────

    def _collect_speech(self):
        """
        Blocks until a complete speech utterance is collected.
        Returns numpy array of speech audio, or None if nothing detected.
        """
        import numpy as np
        if self._vad_model is None:
            self._load_vad()

        speech_frames = []
        in_speech = False
        silence_start = None
        SPEECH_THRESH = 0.5
        SILENCE_THRESH = 0.3

        while True:
            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                if in_speech and silence_start:
                    if time.time() - silence_start > SILENCE_TIMEOUT:
                        break
                continue

            prob = self._speech_prob(chunk)

            if prob >= SPEECH_THRESH:
                if not in_speech:
                    in_speech = True
                    log.debug("Speech start (prob=%.2f)", prob)
                silence_start = None
                speech_frames.append(chunk)
            elif in_speech:
                speech_frames.append(chunk)
                if prob < SILENCE_THRESH:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > SILENCE_TIMEOUT:
                        break

        if not speech_frames:
            return None

        audio = np.concatenate(speech_frames)
        if len(audio) / SAMPLE_RATE < MIN_SPEECH_SECONDS:
            log.debug("Clip too short (%.2fs), skipping", len(audio) / SAMPLE_RATE)
            return None

        return audio

    # ── Main loop ─────────────────────────────────────────────────

    async def run(self) -> None:
        """Main voice loop: listen → transcribe → send to INANNA."""
        try:
            import sounddevice as sd
        except ImportError:
            raise ImportError(
                "sounddevice not installed. Run: pip install sounddevice"
            )
        import websockets

        self._load_whisper()
        self._load_vad()

        print()
        print("𒀭 INANNA Voice Listener")
        print(f"   Model    : {self.model_size}")
        print(f"   Language : {self.language or 'auto-detect'}")
        print(f"   Server   : {self.ws_url}")
        print(f"   Device   : {self.device}")
        print()
        print("   Listening... Speak to INANNA. Ctrl+C to stop.")
        print()

        ws_conn = None

        async def get_ws():
            nonlocal ws_conn
            try:
                if ws_conn is None:
                    ws_conn = await websockets.connect(self.ws_url)
                return ws_conn
            except Exception as e:
                log.warning("WebSocket: %s", e)
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
                        log.warning("Send failed: %s", e)
                        ws_conn = None
                else:
                    print(f"       (not connected — text not sent)")


def main() -> None:
    parser = argparse.ArgumentParser(description="INANNA NYX Voice Listener")
    parser.add_argument("--model", default="base",
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--lang", default=None,
                        help="Language: es, en, pt (omit = auto)")
    parser.add_argument("--ws", default="ws://localhost:8081",
                        help="INANNA WebSocket URL")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                        help="Inference device")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
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
    except ImportError as e:
        print(f"\nMissing dependency: {e}")
        print("Install: pip install faster-whisper sounddevice torch")
        sys.exit(1)


if __name__ == "__main__":
    main()
