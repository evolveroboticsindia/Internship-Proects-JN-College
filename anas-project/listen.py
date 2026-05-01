"""
listen.py — VAD listener, active only when a face is detected.

Flow:
  1. Mic streams audio 24/7.
  2. If no face is present → all audio is ignored.
  3. Face present + RMS crosses SPEECH_THRESHOLD → start recording.
  4. RMS stays below SILENCE_THRESHOLD for SILENCE_SEC → stop & transcribe.
  5. on_speech(text) is called with the result.
"""

import threading
import collections
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

# ── CONFIG ────────────────────────────────────────────────────────────────────
SAMPLE_RATE       = 16000
CHUNK_SIZE        = 512       # ~32 ms per chunk

SPEECH_THRESHOLD  = 0.015     # RMS to start recording — raise if noisy room
SILENCE_THRESHOLD = 0.010     # RMS below this = silence
SILENCE_SEC       = 1.5       # seconds of silence before we stop recording
MAX_RECORD_SEC    = 10        # hard cap
PRE_BUFFER_CHUNKS = 12        # ~384 ms pre-roll so first syllable isn't clipped

DEVICE = None                 # set to mic index/name if needed

# ── FACE FLAG — set by track.py ───────────────────────────────────────────────
_face_present = False
_face_lock    = threading.Lock()

def set_face_present(val: bool):
    global _face_present
    with _face_lock:
        _face_present = val

def _face_here() -> bool:
    with _face_lock:
        return _face_present

# ── SPEAKING FLAG — set by app.py so mic mutes while robot talks ──────────────
_robot_speaking = False
_speaking_lock  = threading.Lock()

def set_robot_speaking(val: bool):
    """Call with True before speak(), False after. Prevents mic feedback loop."""
    global _robot_speaking
    with _speaking_lock:
        _robot_speaking = val

def _robot_is_speaking() -> bool:
    with _speaking_lock:
        return _robot_speaking

# ── MODEL ─────────────────────────────────────────────────────────────────────
print("[LISTEN] Loading Whisper model...")
model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
print("[LISTEN] Ready.")

# ── TRANSCRIBE ────────────────────────────────────────────────────────────────
def _transcribe(audio: np.ndarray) -> str:
    segments, _ = model.transcribe(
        audio,
        beam_size                   = 1,
        vad_filter                  = True,   # filters non-speech internally
        condition_on_previous_text  = False,  # prevents hallucination chaining
        compression_ratio_threshold = 1.8,    # catches repetitive hallucinations
    )
    return "".join(seg.text for seg in segments).strip()

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
def start_listening(on_speech):
    SILENCE_LIMIT = int(SILENCE_SEC    * SAMPLE_RATE / CHUNK_SIZE)
    MAX_CHUNKS    = int(MAX_RECORD_SEC * SAMPLE_RATE / CHUNK_SIZE)

    pre_buffer = collections.deque(maxlen=PRE_BUFFER_CHUNKS)
    processing = threading.Event()

    state = {
        "recording":     False,
        "chunks":        [],
        "silence_count": 0,
    }

    def callback(indata, frames, time_info, status):
        chunk = indata.copy().flatten()
        rms   = float(np.sqrt(np.mean(chunk ** 2)))

        # keep pre-buffer rolling regardless
        if not state["recording"]:
            pre_buffer.append(chunk)

        # mute while robot is speaking (feedback prevention)
        if _robot_is_speaking():
            if state["recording"]:
                state["recording"]     = False
                state["chunks"]        = []
                state["silence_count"] = 0
            return

        # no face → block NEW recordings, but let an ongoing recording finish
        if not _face_here():
            if not state["recording"]:
                return

        if not state["recording"]:
            if rms > SPEECH_THRESHOLD:
                state["recording"]     = True
                state["chunks"]        = list(pre_buffer)
                state["silence_count"] = 0
                print("[LISTEN] 🎙 Recording…")
        else:
            state["chunks"].append(chunk)
            state["silence_count"] = (
                state["silence_count"] + 1 if rms < SILENCE_THRESHOLD else 0
            )

            if state["silence_count"] >= SILENCE_LIMIT or len(state["chunks"]) >= MAX_CHUNKS:
                audio = np.concatenate(state["chunks"]).astype(np.float32)
                peak  = np.max(np.abs(audio))
                if peak > 0:
                    audio = (audio / peak) * 0.8

                state["recording"]     = False
                state["chunks"]        = []
                state["silence_count"] = 0

                if not processing.is_set():
                    processing.set()
                    def process(a):
                        try:
                            print("[LISTEN] Transcribing…")
                            text = _transcribe(a)
                            if text:
                                print(f"[LISTEN] Heard: '{text}'")
                            on_speech(text)
                        finally:
                            processing.clear()
                    threading.Thread(target=process, args=(audio,), daemon=True).start()
                else:
                    print("[LISTEN] Still processing — skipped.")

    print("[LISTEN] Listening. Waiting for a face…")
    with sd.InputStream(
        samplerate = SAMPLE_RATE,
        channels   = 1,
        dtype      = "float32",
        blocksize  = CHUNK_SIZE,
        device     = DEVICE,
        callback   = callback,
    ):
        threading.Event().wait()