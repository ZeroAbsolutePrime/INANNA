# INANNA NYX Voice Listener

Speak to INANNA. She hears you.

## Install Dependencies

```bash
pip install faster-whisper sounddevice torch
```

On Windows, sounddevice works out of the box (PortAudio bundled).
On NixOS: `nix-env -iA nixpkgs.portaudio` first.

## Start the Voice Listener

Start the INANNA server first, then in a separate terminal:

```bash
cd inanna

# Auto-detect language, base model (145MB)
python -m voice.listener

# Spanish, small model (better accuracy)
python -m voice.listener --lang es --model small

# English with debug output
python -m voice.listener --lang en --debug

# Connect to INANNA on another machine
python -m voice.listener --ws ws://192.168.1.100:8081
```

## Model Sizes

| Model    | Size   | Speed  | Accuracy  | Recommended for    |
|----------|--------|--------|-----------|-------------------|
| tiny     | 75MB   | Fast   | Low       | Testing only       |
| base     | 145MB  | Good   | Good      | CPU, daily use     |
| small    | 244MB  | Medium | Better    | CPU, best balance  |
| medium   | 769MB  | Slow   | High      | Good CPU or GPU    |
| large-v3 | 1.5GB  | Slow   | Best      | GPU recommended    |

**Recommended:** `--model base` for CPU, `--model small` for more accuracy.

## Languages Supported

INANNA NAMMU's languages:
- `--lang es` — Spanish
- `--lang en` — English  
- `--lang pt` — Portuguese
- *(omit)* — Auto-detect (slightly slower)

## How It Works

```
Microphone
    ↓
sounddevice (captures at 16kHz)
    ↓
Silero VAD (detects speech start/end)
    ↓
Speech buffer assembled
    ↓
faster-whisper (transcribes)
    ↓
WebSocket → INANNA server (port 8081)
    ↓
INANNA responds in the browser
```

## Latency Budget (base model, CPU)

| Step           | Time    |
|----------------|---------|
| VAD detection  | ~30ms   |
| Whisper (5s speech) | 1-3s |
| WebSocket send | ~5ms    |
| INANNA process | 2-10s   |
| **Total**      | **3-13s** |

## Troubleshooting

**No audio detected:**
- Check microphone permissions in Windows Settings
- Try `python -m voice.listener --debug` to see VAD probabilities

**ImportError: No module named 'faster_whisper':**
- Run: `pip install faster-whisper`

**ImportError: No module named 'sounddevice':**
- Run: `pip install sounddevice`

**"Not connected" — text not sent:**
- Make sure INANNA server is running: `python ui_main.py`
- Check that port 8081 is not blocked

**High latency:**
- Use `--model tiny` for fastest response
- Or use `--device cuda` if you have a compatible GPU
