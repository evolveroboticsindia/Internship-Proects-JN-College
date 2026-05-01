import asyncio
import websockets
import subprocess
import json
import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer

print("🚀 OFFLINE AI SERVER STARTING...")

# =========================
# 🧠 VOSK MODEL
# =========================
model = Model("model")
recognizer = KaldiRecognizer(model, 16000)

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

# =========================
# 🤖 AI (OLLAMA)
# =========================
def ask_ai(prompt):
    try:
        result = subprocess.run(
            ["ollama", "run", "phi", prompt],
            capture_output=True,
            text=True,
            timeout=20
        )
        reply = result.stdout.strip()
        return reply if reply else "I didn't understand that."
    except Exception as e:
        print("❌ AI Error:", e)
        return "AI error."

# =========================
# 🌐 CLIENTS
# =========================
clients = set()

async def broadcast(message):
    print("📡 Sending:", message)
    print("👥 Clients:", len(clients))

    dead = []
    for ws in clients:
        try:
            await ws.send(message)
        except:
            dead.append(ws)

    for ws in dead:
        clients.remove(ws)

# =========================
# 🔌 WEBSOCKET
# =========================
async def handler(ws):
    print("🟢 UI Connected")
    clients.add(ws)

    try:
        await ws.wait_closed()
    finally:
        clients.remove(ws)
        print("🔴 UI Disconnected")

# =========================
# 🚀 MAIN LOOP
# =========================
async def main():
    WAKE = "hey robo"
    SLEEP = "sleep"
    active = False

    async with websockets.serve(handler, "127.0.0.1", 5678):
        print("✅ Running on ws://127.0.0.1:5678")
        print("🎤 Listening...")

        with sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype='int16',
            channels=1,
            callback=callback
        ):
            while True:
                data = q.get()

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").lower().strip()

                    if not text:
                        continue

                    print("🗣️ Heard:", text)

                    if WAKE in text:
                        active = True
                        await broadcast("Yes buddy 😊")
                        continue

                    if SLEEP in text:
                        active = False
                        await broadcast("Going to sleep 😴")
                        continue

                    if not active:
                        continue

                    reply = ask_ai(text)
                    print("🤖 AI:", reply)

                    await broadcast(reply)

asyncio.run(main())