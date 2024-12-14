from flask import Flask, Response
import cv2
import threading
import time
from dotenv import load_dotenv
import os

load_dotenv()

ONVIF_USERNAME = os.getenv('ONVIF_USERNAME')
ONVIF_PASSWORD = os.getenv('ONVIF_PASSWORD')
ONVIF_IP = os.getenv('ONVIF_IP')

auth = f"{ONVIF_USERNAME}:{ONVIF_PASSWORD}@{ONVIF_IP}"

app = Flask(__name__)

# Global variables for frame sharing
frame = None
lock = threading.Lock()

def generate_frames():
    global frame
    while True:
        with lock:
            if frame is not None:
                # Encode frame as JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.03)  # ~30 FPS

def capture_frames():
    global frame
    # RTSP stream URL
    stream_url = f"rtsp://{auth}:554/ch01/0"
    cap = cv2.VideoCapture(stream_url)
    
    while True:
        ret, new_frame = cap.read()
        if ret:
            with lock:
                frame = new_frame
        else:
            print("Failed to get frame, retrying in 5 seconds...")
            time.sleep(5)
            cap = cv2.VideoCapture(stream_url)

@app.route('/')
def index():
    return """
    <html>
        <head>
            <title>RTSP Stream</title>
            <style>
                body { margin: 0; background: #000; }
                img { max-width: 100%; height: auto; }
                .container { display: flex; justify-content: center; align-items: center; height: 100vh; }
            </style>
        </head>
        <body>
            <div class="container">
                <img src="/video_feed">
            </div>
        </body>
    </html>
    """

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Start frame capture in a separate thread
    threading.Thread(target=capture_frames, daemon=True).start()
    app.run(host='0.0.0.0', port=8083)
