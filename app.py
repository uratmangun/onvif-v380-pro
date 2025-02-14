from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
import subprocess
import signal
import atexit
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

ONVIF_USERNAME = os.getenv('ONVIF_USERNAME')
ONVIF_PASSWORD = os.getenv('ONVIF_PASSWORD')
ONVIF_IP = os.getenv('ONVIF_IP')

if not all([ONVIF_USERNAME, ONVIF_PASSWORD, ONVIF_IP]):
    logger.error("Missing required environment variables!")
    raise ValueError("Missing required environment variables!")

auth = f"{ONVIF_USERNAME}:{ONVIF_PASSWORD}@{ONVIF_IP}"
stream_url = f"rtsp://{auth}:554/ch01/0"

app = Flask(__name__)
# Configure CORS to allow requests from your domain
CORS(app, resources={
    r"/*": {
        "origins": ["https://onvif.uratmangun.ovh"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Add CORS headers for HLS files
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'https://onvif.uratmangun.ovh')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    if request.path.endswith(('.m3u8', '.ts')):
        response.headers.add('Cache-Control', 'no-cache, no-store, must-revalidate')
        response.headers.add('Pragma', 'no-cache')
        response.headers.add('Expires', '0')
    return response

# Global variable for FFmpeg process
ffmpeg_process = None

def start_ffmpeg():
    global ffmpeg_process
    if ffmpeg_process is None:
        try:
            logger.info("Starting FFmpeg process...")
            
            # Ensure the hls directory exists and has proper permissions
            os.makedirs('static/hls', exist_ok=True)
            os.chmod('static/hls', 0o777)
            
            # Clean up any existing HLS files
            for file in os.listdir('static/hls'):
                file_path = os.path.join('static/hls', file)
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up {file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up {file_path}: {e}")
            
            command = [
                'ffmpeg',
                '-y',
                '-fflags', 'nobuffer+genpts+igndts+discardcorrupt+flush_packets',
                '-flags', 'low_delay',
                '-rtsp_transport', 'tcp',
                '-rtsp_flags', 'prefer_tcp',
                '-probesize', '32',
                '-analyzeduration', '0',
                '-timeout', '5000000',
                '-use_wallclock_as_timestamps', '1',
                '-i', stream_url,
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-profile:v', 'baseline',
                '-level', '3.0',
                '-fps_mode', 'cfr',
                '-r', '30',
                '-g', '30',
                '-keyint_min', '30',
                '-sc_threshold', '0',
                '-bufsize', '2000k',
                '-maxrate', '2000k',
                '-crf', '28',
                '-pix_fmt', 'yuv420p',
                '-x264-params', 'no-scenecut=1:rc-lookahead=0:sync-lookahead=0:ref=1:bframes=0:b-adapt=0:force-cfr=1',
                '-max_muxing_queue_size', '1024',
                '-f', 'hls',
                '-method', 'PUT',
                '-hls_time', '1',
                '-hls_init_time', '1',
                '-hls_list_size', '3',
                '-hls_flags', 'delete_segments+discont_start+omit_endlist+independent_segments',
                '-hls_segment_type', 'mpegts',
                '-hls_allow_cache', '0',
                '-start_number', '0',
                '-hls_segment_filename', 'static/hls/segment_%03d.ts',
                'static/hls/playlist.m3u8'
            ]
            
            logger.info("FFmpeg command: %s", ' '.join(command))
            
            # Start ffmpeg process and capture output
            ffmpeg_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Wait for the playlist file to be created
            max_wait = 10  # Maximum wait time in seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                if ffmpeg_process.poll() is not None:
                    error = ffmpeg_process.stderr.read() if ffmpeg_process.stderr else "No error output"
                    logger.error(f"FFmpeg process died: {error}")
                    return False
                
                if os.path.exists('static/hls/playlist.m3u8'):
                    logger.info("Playlist file created successfully")
                    return True
                
                time.sleep(0.5)
            
            logger.error("Timeout waiting for playlist file")
            stop_ffmpeg()
            return False
            
        except Exception as e:
            logger.error(f"Error starting FFmpeg: {e}")
            if ffmpeg_process:
                stop_ffmpeg()
            return False
    return True  # Return True if process is already running

def stop_ffmpeg():
    global ffmpeg_process
    if ffmpeg_process:
        try:
            logger.info("Stopping FFmpeg process...")
            ffmpeg_process.send_signal(signal.SIGTERM)
            ffmpeg_process.wait(timeout=5)
            ffmpeg_process = None
            logger.info("FFmpeg process stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping FFmpeg: {e}")
            try:
                ffmpeg_process.kill()
            except:
                pass
            ffmpeg_process = None
            return False
    return False

# Register cleanup function
atexit.register(stop_ffmpeg)

@app.route('/hls/<path:filename>')
def serve_hls(filename):
    return send_from_directory('static/hls', filename)

@app.route('/stream/start', methods=['POST'])
def start_stream():
    try:
        if ffmpeg_process and ffmpeg_process.poll() is None:
            return jsonify({"status": "success", "message": "Stream already running"})
        
        if start_ffmpeg():
            return jsonify({"status": "success", "message": "Stream started"})
        else:
            logger.error("Failed to start FFmpeg process")
            return jsonify({
                "status": "error",
                "message": "Failed to start stream. Please check server logs for details."
            }), 500
    except Exception as e:
        logger.exception("Error in start_stream route")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/stream/stop', methods=['POST'])
def stop_stream():
    try:
        if stop_ffmpeg():
            return jsonify({"status": "success", "message": "Stream stopped"})
        return jsonify({"status": "error", "message": "Stream not running or failed to stop"}), 400
    except Exception as e:
        logger.exception("Error in stop_stream route")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/stream/status')
def stream_status():
    try:
        is_running = ffmpeg_process and ffmpeg_process.poll() is None
        has_playlist = os.path.exists('static/hls/playlist.m3u8')
        
        status = "running" if is_running and has_playlist else "stopped"
        return jsonify({
            "status": status,
            "has_playlist": has_playlist,
            "process_running": is_running
        })
    except Exception as e:
        logger.exception("Error in stream_status route")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

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
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    font-family: Arial, sans-serif;
                }
                #player {
                    width: 100%;
                    max-width: 1280px;
                    height: auto;
                    aspect-ratio: 16/9;
                    margin-bottom: 20px;
                }
                .controls {
                    display: flex;
                    gap: 10px;
                    margin-top: 20px;
                }
                button {
                    padding: 10px 20px;
                    font-size: 16px;
                    cursor: pointer;
                    border: none;
                    border-radius: 5px;
                    background: #2196F3;
                    color: white;
                    transition: background 0.3s;
                }
                button:hover {
                    background: #1976D2;
                }
                button:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                }
                #status {
                    color: white;
                    margin-top: 10px;
                    font-size: 14px;
                }
            </style>
            <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/@clappr/player@latest/dist/clappr.min.js"></script>
        </head>
        <body>
            <div id="player"></div>
            <div class="controls">
                <button id="startBtn" onclick="controlStream('start')">Start Stream</button>
                <button id="stopBtn" onclick="controlStream('stop')">Stop Stream</button>
            </div>
            <div id="status"></div>
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
                        liveSyncDurationCount: 1,
                        liveMaxLatencyDurationCount: 2,
                        maxBufferSize: 1 * 1000 * 1000,
                        maxBufferLength: 2,
                        manifestLoadingTimeOut: 1000,
                        manifestLoadingMaxRetry: 2,
                        manifestLoadingRetryDelay: 500,
                        levelLoadingTimeOut: 1000,
                        levelLoadingMaxRetry: 2,
                        levelLoadingRetryDelay: 500,
                        fragLoadingTimeOut: 1000,
                        fragLoadingMaxRetry: 2,
                        fragLoadingRetryDelay: 500,
                        startFragPrefetch: false,
                        appendErrorMaxRetry: 2,
                        testBandwidth: false,
                        progressive: false,
                        backBufferLength: 0,
                        enableStreamingMode: true,
                        liveDurationInfinity: true,
                        liveBackBufferLength: 0,
                        maxMaxBufferLength: 2,
                        liveSyncDuration: 0.5,
                        liveMaxLatencyDuration: 2,
                        maxLiveSyncPlaybackRate: 1.2,
                        liveSyncDurationCount: 1,
                        abrEwmaDefaultEstimate: 500000
                    }
                });

                // Handle player errors with more aggressive recovery
                player.on(Clappr.Events.PLAYER_ERROR, function(error) {
                    console.error('Player error:', error);
                    setTimeout(() => {
                        console.log('Attempting to reconnect...');
                        player.configure({
                            hlsjsConfig: {
                                manifestLoadingTimeOut: 1000,
                                manifestLoadingMaxRetry: 2,
                                manifestLoadingRetryDelay: 500,
                                levelLoadingTimeOut: 1000,
                                levelLoadingMaxRetry: 2,
                                levelLoadingRetryDelay: 500,
                                fragLoadingTimeOut: 1000,
                                fragLoadingMaxRetry: 2,
                                fragLoadingRetryDelay: 500
                            }
                        });
                        player.load('/hls/playlist.m3u8');
                    }, 1000);
                });

                // Update the stall detection in the HTML/JavaScript section
                let lastPosition = 0;
                let lastStallCheck = Date.now();
                const STALL_THRESHOLD = 3000; // 3 seconds
                const MIN_MOVEMENT = 0.1; // Minimum movement threshold

                // Function to check if player is in loading state
                function isPlayerLoading() {
                    const loadingElement = document.querySelector('.player-loading');
                    const bufferingElement = document.querySelector('.spinner-three-bounce');
                    return (loadingElement && loadingElement.style.display !== 'none') || 
                           (bufferingElement && bufferingElement.style.display !== 'none');
                }

                // Function to check if player is actually playing
                function isActuallyPlaying() {
                    return player && 
                           player.isPlaying() && 
                           !isPlayerLoading() && 
                           player.getCurrentTime() > 0;
                }

                let bufferingCount = 0;
                let lastBufferingTime = Date.now();
                const BUFFERING_RESET_INTERVAL = 30000; // Reset buffering count after 30 seconds
                const MAX_BUFFERING_COUNT = 3; // Maximum allowed buffering occurrences

                async function handleExcessiveBuffering() {
                    console.log('Excessive buffering detected, restarting stream...');
                    await controlStream('stop');
                    setTimeout(async () => {
                        await controlStream('start');
                    }, 2000);
                    bufferingCount = 0;
                }

                setInterval(() => {
                    // Reset buffering count if enough time has passed
                    if (Date.now() - lastBufferingTime > BUFFERING_RESET_INTERVAL) {
                        bufferingCount = 0;
                    }

                    if (isActuallyPlaying()) {
                        const currentPosition = player.getCurrentTime();
                        const currentTime = Date.now();
                        const timeDiff = currentTime - lastStallCheck;
                        
                        if (timeDiff >= STALL_THRESHOLD) {
                            if (Math.abs(currentPosition - lastPosition) < MIN_MOVEMENT) {
                                document.getElementById('status').textContent = 'Stream status: Stream stopped or buffering';
                            } else {
                                document.getElementById('status').textContent = 'Stream status: running';
                            }
                            lastPosition = currentPosition;
                            lastStallCheck = currentTime;
                        }
                    } else if (player && !player.isPlaying()) {
                        document.getElementById('status').textContent = 'Stream status: Stream stopped';
                    } else if (isPlayerLoading()) {
                         bufferingCount++;
                    lastBufferingTime = Date.now();
                    console.log('Buffering count:', bufferingCount);
                    
                    if (bufferingCount >= MAX_BUFFERING_COUNT) {
                        document.getElementById('status').textContent = `Stream status: Buffering (Count: ${bufferingCount}) - Restarting stream due to excessive buffering...`;
                        handleExcessiveBuffering();
                    } else {
                        document.getElementById('status').textContent = `Stream status: Buffering (Count: ${bufferingCount})`;
                    }
                    }
                }, 1000);

                player.on(Clappr.Events.PLAYBACK_PLAY, function() {
                    lastPosition = player.getCurrentTime();
                });

                player.on(Clappr.Events.PLAYBACK_BUFFERING, function() {
                    bufferingCount++;
                    lastBufferingTime = Date.now();
                    console.log('Buffering count:', bufferingCount);
                    
                    if (bufferingCount >= MAX_BUFFERING_COUNT) {
                        document.getElementById('status').textContent = `Stream status: Buffering (Count: ${bufferingCount}) - Restarting stream due to excessive buffering...`;
                        handleExcessiveBuffering();
                    } else {
                        document.getElementById('status').textContent = `Stream status: Buffering (Count: ${bufferingCount})`;
                    }
                });

                player.on(Clappr.Events.PLAYBACK_BUFFERFULL, function() {
                    document.getElementById('status').textContent = 'Stream status: running';
                });

                player.on(Clappr.Events.PLAYBACK_STOP, function() {
                    document.getElementById('status').textContent = 'Stream status: Stream stopped';
                });

                function updateButtons(status) {
                    document.getElementById('startBtn').disabled = status === 'running';
                    document.getElementById('stopBtn').disabled = status === 'stopped';
                    document.getElementById('status').textContent = `Stream status: ${status}`;
                }

                async function controlStream(action) {
                    try {
                        const response = await fetch(`/stream/${action}`, {
                            method: 'POST'
                        });
                        const data = await response.json();
                        
                        if (response.ok) {
                            if (action === 'start') {
                                // Wait for FFmpeg to start and create the playlist
                                setTimeout(() => {
                                    player.load('/hls/playlist.m3u8');
                                }, 3000);
                            } else if (action === 'stop') {
                                player.stop();
                            }
                            // Only check status after successful response
                            checkStatus();
                        } else {
                            console.error('Server error:', data.message);
                        }
                    } catch (error) {
                        console.error('Error:', error);
                    }
                }

                async function checkStatus() {
                    try {
                        const response = await fetch('/stream/status');
                        const data = await response.json();
                        updateButtons(data.status);
                        
                        // If stream is running but player is stopped, try to restart
                        if (data.status === 'running' && !player.isPlaying()) {
                            player.load('/hls/playlist.m3u8');
                        }
                    } catch (error) {
                        console.error('Error:', error);
                    }
                }

                // Check status more frequently initially, then less frequently
                checkStatus();
                setInterval(checkStatus, 5000);
            </script>
        </body>
    </html>
    """

if __name__ == '__main__':
    start_ffmpeg()
    app.run(host='0.0.0.0', port=8083)
