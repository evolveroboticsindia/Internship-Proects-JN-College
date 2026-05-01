"""
app.py — Robot assistant Flask backend.
Start:  python app.py
Open:   http://localhost:5000
Behaviour:
  • Face visible  → robot listens and responds automatically.
  • No face       → robot is silent and ignores all audio.
"""
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO
from brain  import get_reply
from speak  import speak
from listen import start_listening, set_robot_speaking
from track  import start_tracking

app      = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

busy      = False
busy_lock = threading.Lock()


def handle_speech(text: str):
    global busy
    with busy_lock:
        if busy:
            return
        busy = True
    try:
        if not text:
            socketio.emit("state", {"state": "idle"})
            return

        socketio.emit("state", {"state": "think"})
        reply = get_reply(text)
        print(f"[APP] Replying: {reply}")

        socketio.emit("state", {"state": "speak"})
        set_robot_speaking(True)   # mute mic — robot is about to talk
        try:
            speak(reply)
        finally:
            set_robot_speaking(False)  # always unmute, even if speak() crashes

        socketio.emit("state", {"state": "idle"})
        socketio.emit("chat", {"role": "user",  "text": text})
        socketio.emit("chat", {"role": "robot", "text": reply})
    finally:
        with busy_lock:
            busy = False


@app.route("/")
def index():
    return render_template("robot-face.html")


if __name__ == "__main__":
    threading.Thread(
        target=start_listening,
        args=(handle_speech,),
        daemon=True,
    ).start()
    start_tracking(socketio)
    print("\n[APP] Running → http://localhost:5000")
    print("[APP] Robot listens automatically when a face is detected.\n")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)