import cv2
import asyncio
import websockets
import json

print("📷 Face tracking starting...")

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

clients = set()

async def handler(ws):
    print("🟢 Face client connected")
    clients.add(ws)

    try:
        await ws.wait_closed()
    finally:
        clients.remove(ws)
        print("🔴 Face client disconnected")

async def camera_loop():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Camera error")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        h, w = frame.shape[:2]

        if len(faces) > 0:
            x, y, fw, fh = faces[0]

            cx = (x + fw/2 - w/2) / (w/2)
            cy = (y + fh/2 - h/2) / (h/2)

            data = json.dumps({"x": cx, "y": cy})

            for c in list(clients):
                try:
                    await c.send(data)
                except:
                    clients.remove(c)

        cv2.imshow("Camera", frame)

        if cv2.waitKey(1) == 27:
            break

        await asyncio.sleep(0.03)

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("✅ Face WS running on 8765")
        await camera_loop()

asyncio.run(main())