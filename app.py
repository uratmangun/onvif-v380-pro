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
            '-fflags', 'nobuffer+discardcorrupt',
            '-flags', 'low_delay',
            '-strict', 'experimental',
            '-rtsp_transport', 'tcp',
            '-i', stream_url,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-vsync', '0',
            '-copyts',
            '-x264-params', 'keyint=14:min-keyint=14:scenecut=0:force-cfr=0',
            '-r', '14',
            '-g', '14',
            '-f', 'hls',
            '-hls_time', '0.5',
            '-hls_list_size', '2',
            '-hls_flags', 'delete_segments+omit_endlist+independent_segments',
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

@app.route('/hls/<path:filename>')
def serve_hls(filename):
    return send_from_directory('/app/static/hls', filename)

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
                #player {
                    width: 100%;
                    max-width: 1280px;
                    height: auto;
                    aspect-ratio: 16/9;
                }
            </style>
            <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/@clappr/player@latest/dist/clappr.min.js"></script>
        </head>
        <body>
            <div id="player"></div>
            <script>
                var player = new Clappr.Player({
                    source: '/hls/playlist.m3u8',
                    parentId: '#player',
                    width: '100%',
                    height: '100%',
                    autoPlay: true,
                    mute: true,
                    playback: {
                        playInline: true,
                        hlsMinimumDvrSize: 0
                    },
                    hlsjsConfig: {
                        debug: false,
                        enableWorker: true,
                        lowLatencyMode: true,
                        backBufferLength: 30,
                        liveSyncDurationCount: 3,
                        liveMaxLatencyDurationCount: 6,
                        maxBufferLength: 30,
                        maxBufferSize: 10 * 1000 * 1000,
                        maxBufferHole: 0.5,
                        highBufferWatchdogPeriod: 1
                    }
                });
            </script>
        </body>
    </html>
    """

if __name__ == '__main__':
    start_ffmpeg()
    app.run(host='0.0.0.0', port=8083)
