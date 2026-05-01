"""
speak.py — TTS using Piper (offline, Linux)

Piper is a fast neural TTS engine.
Binary + voice model are stored locally under models/piper/.

Fallback: if Piper is not found, falls back to espeak-ng (always installed).
"""

import os
import subprocess
import tempfile
import sounddevice as sd
import soundfile as sf

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PIPER_EXE   = os.path.join(BASE_DIR, "models", "piper", "piper")          # Linux binary (no .exe)
VOICE_MODEL = os.path.join(BASE_DIR, "models", "piper", "voices",
                            "en_US-lessac-high.onnx")
TMP_WAV     = os.path.join(BASE_DIR, "data", "speech.wav")


def _speak_piper(text: str) -> bool:
    """Try Piper. Returns True on success, False if unavailable."""
    if not os.path.exists(PIPER_EXE):
        print(f"[SPEAK] Piper binary not found at: {PIPER_EXE}")
        return False
    if not os.path.exists(VOICE_MODEL):
        print(f"[SPEAK] Voice model not found at: {VOICE_MODEL}")
        return False

    os.makedirs(os.path.dirname(TMP_WAV), exist_ok=True)

    try:
        proc = subprocess.run(
            [PIPER_EXE, "--model", VOICE_MODEL, "--output_file", TMP_WAV],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=15,
        )
        if proc.returncode != 0:
            print(f"[SPEAK] Piper error: {proc.stderr.decode()}")
            return False
    except Exception as e:
        print(f"[SPEAK] Failed to run Piper: {e}")
        return False

    try:
        data, samplerate = sf.read(TMP_WAV)
        sd.play(data, samplerate)
        sd.wait()
        return True
    except Exception as e:
        print(f"[SPEAK] Playback error: {e}")
        return False


def _speak_espeak(text: str):
    """Fallback: espeak-ng (install via: sudo dnf install espeak-ng)."""
    try:
        subprocess.run(
            ["espeak-ng", "-v", "en-us", "-s", "150", text],
            timeout=15,
            check=True,
        )
    except FileNotFoundError:
        print("[SPEAK] espeak-ng not found. Install it: sudo dnf install espeak-ng")
    except Exception as e:
        print(f"[SPEAK] espeak-ng error: {e}")


def speak(text: str):
    if not text:
        return
    print(f"[SPEAK] → {text!r}")
    if not _speak_piper(text):
        print("[SPEAK] Falling back to espeak-ng…")
        _speak_espeak(text)
