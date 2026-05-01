"""
track.py — Face tracking using OpenCV.

Detects the closest (largest) face via Haar cascade.
Emits 'gaze' events to the frontend via SocketIO.
Calls listen.set_face_present() to enable/disable the microphone.
"""

import threading
import time
import cv2
from listen import set_face_present

CAMERA_INDEX     = 0      # change to 1 for external USB cam
FRAME_INTERVAL   = 0.05   # ~20 fps
SMOOTHING        = 0.2
NO_FACE_RESET    = 2.0    # seconds before eyes drift back to centre
FACE_LOST_FRAMES = 10     # consecutive no-face frames before we say "gone"

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


def start_tracking(socketio_instance):
    threading.Thread(
        target=_tracking_loop,
        args=(socketio_instance,),
        daemon=True,
    ).start()
    print("[TRACK] Face tracking started.")


def _tracking_loop(socketio):
    cascade = cv2.CascadeClassifier(CASCADE_PATH)
    if cascade.empty():
        print("[TRACK] ERROR: Haar cascade not found. Tracking disabled.")
        return

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[TRACK] ERROR: Cannot open camera {CAMERA_INDEX}.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FPS, 20)

    gaze_x, gaze_y   = 0.0, 0.0
    last_face_time   = time.time()
    no_face_streak   = 0
    face_was_present = False

    print(f"[TRACK] Camera {CAMERA_INDEX} opened.")

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.2)
            continue

        h, w  = frame.shape[:2]
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40)
        )

        if len(faces) > 0:
            no_face_streak = 0

            if not face_was_present:
                face_was_present = True
                set_face_present(True)
                socketio.emit("state", {"state": "listen"})
                print("[TRACK] 👤 Face detected — listener active.")

            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            cx = (x + fw / 2) / w
            cy = (y + fh / 2) / h

            target_x = -(cx - 0.5) * 2
            target_y =  (cy - 0.5) * 2

            gaze_x += (target_x - gaze_x) * (1 - SMOOTHING)
            gaze_y += (target_y - gaze_y) * (1 - SMOOTHING)
            last_face_time = time.time()

        else:
            no_face_streak += 1
            if no_face_streak >= FACE_LOST_FRAMES and face_was_present:
                face_was_present = False
                set_face_present(False)
                socketio.emit("state", {"state": "idle"})
                print("[TRACK] 👻 Face lost — listener paused.")

            if time.time() - last_face_time > NO_FACE_RESET:
                gaze_x += (0.0 - gaze_x) * (1 - SMOOTHING)
                gaze_y += (0.0 - gaze_y) * (1 - SMOOTHING)

        socketio.emit("gaze", {"x": round(gaze_x, 3), "y": round(gaze_y, 3)})
        time.sleep(FRAME_INTERVAL)