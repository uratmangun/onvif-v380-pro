from flask import Flask, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
import subprocess
import signal
import atexit

load_dotenv()

ONVIF_USERNAME = os.getenv('ONVIF_USERNAME')
ONVIF_PASSWORD = os.getenv('ONVIF_PASSWORD')
ONVIF_IP = os.getenv('ONVIF_IP')

auth = f"{ONVIF_USERNAME}:{ONVIF_PASSWORD}@{ONVIF_IP}"
stream_url = f"rtsp://{auth}:554/ch01/0"

app = Flask(__name__)
CORS(app)

# Global variable for FFmpeg process
ffmpeg_process = None

def start_ffmpeg():
    global ffmpeg_process
    if ffmpeg_process is None:
        # Ensure the hls directory exists
        os.makedirs('/app/static/hls', exist_ok=True)
        
        command = [
            'ffmpeg',
            '-i', stream_url,
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-tune', 'zerolatency',
            '-c:a', 'aac',
            '-ar', '44100',
            '-b:a', '128k',
            '-f', 'hls',
            '-hls_time', '2',
            '-hls_list_size', '3',
            '-hls_flags', 'delete_segments+append_list',
            '-hls_segment_filename', '/app/static/hls/segment_%03d.ts',
            '/app/static/hls/playlist.m3u8'
        ]
        ffmpeg_process = subprocess.Popen(command)

def stop_ffmpeg():
    global ffmpeg_process
    if ffmpeg_process:
        ffmpeg_process.send_signal(signal.SIGTERM)
        ffmpeg_process.wait()
        ffmpeg_process = None

# Register cleanup function
atexit.register(stop_ffmpeg)

@app.route('/')
def index():
    return """
    <html>
        <head>
            <title>RTSP Stream</title>
            <style>
                body { 
                    margin: 0; 
                    background: #000;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }
                #video {
                    width: 100%;
                    max-width: 1280px;
                    height: auto;
                    aspect-ratio: 16/9;
                }
            </style>
            <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
        </head>
        <body>
            <video id="video" controls autoplay muted></video>
            <script>
                var video = document.getElementById('video');
                if (Hls.isSupported()) {
                    var hls = new Hls({
                        debug: false,
                        enableWorker: true,
                        lowLatencyMode: true,
                        backBufferLength: 90
                    });
                    
                    hls.loadSource('/hls/playlist.m3u8');
                    hls.attachMedia(video);
                    hls.on(Hls.Events.MEDIA_ATTACHED, function() {
                        video.play();
                    });
                    
                    hls.on(Hls.Events.ERROR, function(event, data) {
                        if (data.fatal) {
                            switch(data.type) {
                                case Hls.ErrorTypes.NETWORK_ERROR:
                                    console.log('Network error, trying to recover...');
                                    hls.startLoad();
                                    break;
                                case Hls.ErrorTypes.MEDIA_ERROR:
                                    console.log('Media error, trying to recover...');
                                    hls.recoverMediaError();
                                    break;
                                default:
                                    console.log('Fatal error, reloading page in 5 seconds...');
                                    setTimeout(() => window.location.reload(), 5000);
                                    break;
                            }
                        }
                    });
                }
                else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                    // For Safari
                    video.src = '/hls/playlist.m3u8';
                }
            </script>
        </body>
    </html>
    """

@app.route('/hls/<path:filename>')
def serve_hls(filename):
    return send_from_directory('/app/static/hls', filename)

if __name__ == '__main__':
    start_ffmpeg()
    app.run(host='0.0.0.0', port=8083)
