# 🤖 Robo — Voice Robot Assistant

A voice-controlled robot face that runs in the browser. It listens to kids, thinks with a local LLM, speaks back with TTS, and its eyes follow the closest person using the camera.

---

## 📁 Project File Structure

```
robo/
├── app.py                  # Flask server — ties everything together
├── brain.py                # LLM logic (Ollama / TinyLlama)
├── listen.py               # Speech-to-text (Whisper via faster-whisper)
├── speak.py                # Text-to-speech (Piper or espeak-ng fallback)
├── track.py                # Face tracking (OpenCV)
├── requirements.txt        # Python dependencies
├── templates/
│   └── robot-face.html     # Browser UI — the robot face
├── models/
│   └── piper/
│       ├── piper           # Piper TTS binary (Linux x86 or ARM)
│       └── voices/
│           └── en_US-lessac-high.onnx   # Voice model
└── data/                   # Auto-created at runtime
    ├── memory.json          # Remembers the child's name
    └── speech.wav           # Temp audio file for TTS
```

---

## 🖥️ Setup on Linux Desktop (x86)

### 1. System packages

```bash
sudo apt update
sudo apt install -y python3-pip espeak-ng portaudio19-dev
```

### 2. Python dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

### 3. Ollama + TinyLlama (the brain)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model
ollama pull tinyllama

# Start Ollama (leave running in background)
ollama serve
```

### 4. Piper TTS (the voice)

Download the Piper binary and voice model and place them at `models/piper/`.

**Binary** — download for Linux x86_64:
```
https://github.com/rhasspy/piper/releases
→ piper_linux_x86_64.tar.gz
```
Extract and place the `piper` binary at:
```
models/piper/piper
chmod +x models/piper/piper
```

**Voice model** — download `en_US-lessac-high.onnx` and its `.json` config:
```
https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/high
```
Place both files at:
```
models/piper/voices/en_US-lessac-high.onnx
models/piper/voices/en_US-lessac-high.onnx.json
```

> If Piper is not found, Robo automatically falls back to `espeak-ng`.

### 5. Run

```bash
python app.py
```

Open `http://localhost:5000` in your browser. Click the face or press `Space` to talk.

---

## 🍓 Raspberry Pi Setup (Ubuntu, ARM64)

Most steps are identical. These are the things that are **different**:

### 1. Piper binary — use the ARM build

Download the ARM64 version instead of x86:
```
https://github.com/rhasspy/piper/releases
→ piper_linux_aarch64.tar.gz
```
Same install path: `models/piper/piper`

### 2. faster-whisper — use a smaller model

The default `tiny.en` model in `listen.py` works on RPi but is slow. It is already the smallest option so no change needed, but expect ~3–5 seconds transcription time on RPi 4.

If it is too slow, you can switch to an even faster CPU mode by editing `listen.py`:

```python
# listen.py line ~14 — already set to tiny, but confirm:
model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
```

### 3. Camera — switch to external USB camera

In `track.py`, change the camera index:

```python
# track.py line 16
CAMERA_INDEX = 0   # internal webcam (desktop)
CAMERA_INDEX = 1   # external USB camera (Raspberry Pi)
```

If you use the official Raspberry Pi Camera Module (not USB), you may need to use `libcamera` instead of OpenCV directly. In that case, replace the `cv2.VideoCapture` line:

```python
# For RPi Camera Module — change this line in track.py:
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
```

### 4. Ollama on Raspberry Pi

Ollama supports ARM64. Install the same way:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull tinyllama
ollama serve
```

TinyLlama runs on RPi 4 (4GB+) but responses will be slower (~5–10 seconds). That is expected.

### 5. Audio — check your output device

On RPi, the default audio output might not be set correctly. Test with:

```bash
speaker-test -t wav -c 2
```

If no sound, set the output device:

```bash
# List devices
python3 -c "import sounddevice; print(sounddevice.query_devices())"

# Set default in speak.py if needed — add device index to sd.play():
sd.play(data, samplerate, device=1)   # change 1 to your device index
```

---

## ⚙️ Quick Reference — What to Change for RPi

| File | Setting | Desktop | Raspberry Pi |
|------|---------|---------|--------------|
| `track.py` | `CAMERA_INDEX` | `0` | `1` (USB) or `0` with `CAP_V4L2` |
| `models/piper/piper` | Binary | `piper_linux_x86_64` | `piper_linux_aarch64` |
| `speak.py` | Audio device | auto | may need `device=N` in `sd.play()` |

Everything else (`brain.py`, `listen.py`, `app.py`, `robot-face.html`) works identically on both platforms.

---

## 🧠 How It Works

```
You speak
   ↓
listen.py  — records audio → Whisper transcribes to text
   ↓
brain.py   — sends text to TinyLlama via Ollama → gets reply
   ↓
speak.py   — sends reply to Piper → plays audio
   ↓
track.py   — OpenCV watches camera → finds closest face
             → sends gaze position to browser via WebSocket
   ↓
robot-face.html — shows animated face, eyes follow you
```

---

## 🛠️ Troubleshooting

**No sound / TTS silent**
- Check `espeak-ng` is installed: `espeak-ng --version`
- Check Piper binary is executable: `chmod +x models/piper/piper`
- On RPi, check audio output device (see above)

**Whisper not loading**
- `pip install faster-whisper --break-system-packages`
- First run downloads the model (~75MB), needs internet

**Camera not opening**
- Check camera index: try `CAMERA_INDEX = 0` then `1`
- Test camera: `python3 -c "import cv2; print(cv2.VideoCapture(0).isOpened())"`

**Ollama not responding**
- Make sure `ollama serve` is running in a separate terminal
- Test: `curl http://localhost:11434/api/generate -d '{"model":"tinyllama","prompt":"hi","stream":false}'`

**Eyes not tracking**
- OpenCV needs camera permission: `sudo usermod -aG video $USER` then log out/in
