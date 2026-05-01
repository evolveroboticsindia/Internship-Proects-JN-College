import queue
import sounddevice as sd
import vosk
import json
import pyttsx3
import requests

# 🔊 Voice
engine = pyttsx3.init()
engine.setProperty('rate', 165)

def speak(text):
    print("Robot:", text)
    engine.say(text)
    engine.runAndWait()

def stop_speaking():
    engine.stop()

# 🤖 AI
def ask_ai(prompt):
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3",
                "prompt": prompt,
                "stream": False
            }
        )
        return res.json()["response"]
    except:
        return "AI not connected"

# 🎤 VOSK
model = vosk.Model("model")
q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

# ⚠️ CHANGE THIS IF MIC NOT WORKING
device = sd.RawInputStream(
    device=1,
    samplerate=16000,
    blocksize=8000,
    dtype='int16',
    channels=1,
    callback=callback
)

rec = vosk.KaldiRecognizer(model, 16000)

print("🤖 Say 'hello' to wake me")

awake = False

with device:
    while True:
        data = q.get()

        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").lower()

            print("You:", text)

            if text == "":
                continue

            # 🛑 STOP TALKING
            if "stop talking" in text:
                stop_speaking()
                continue

            # 👋 WAKE
            if "hello" in text:
                awake = True
                speak("Hello, I am ready")
                continue

            # 😴 SLEEP
            if "sleep" in text:
                speak("Going to sleep")
                awake = False
                continue

            if not awake:
                continue

            # 😊 CUSTOM
            if "how are you" in text:
                speak("I am doing great")
                continue

            # 🤖 AI
            reply = ask_ai(text)
            speak(reply)