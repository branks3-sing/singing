import streamlit as st
import os
import base64
import json
from streamlit.components.v1 import html
import hashlib
from urllib.parse import unquote, quote
import time
import sqlite3
from datetime import datetime
from PIL import Image, ImageDraw
import requests
from io import BytesIO
import subprocess
import tempfile
import re

# =============== LOGO DOWNLOAD AND LOADING ===============
def ensure_logo_exists():
    """Ensure logo exists locally, download from GitHub if not"""
    logo_dir = os.path.join(os.getcwd(), "media", "logo")
    os.makedirs(logo_dir, exist_ok=True)
    
    logo_path = os.path.join(logo_dir, "logoo.png")
    
    if not os.path.exists(logo_path):
        try:
            logo_url = "https://github.com/Swarna-0/karaoke_songs-/raw/main/media/logo/logoo.png"
            response = requests.get(logo_url, timeout=10)
            if response.status_code == 200:
                with open(logo_path, "wb") as f:
                    f.write(response.content)
                print(f"✅ Logo downloaded from GitHub")
            else:
                img = Image.new('RGB', (512, 512), color='#1E3A8A')
                d = ImageDraw.Draw(img)
                d.text((200, 220), "🎤", fill='white', font_size=100)
                img.save(logo_path, 'PNG')
                print(f"✅ Created placeholder logo")
        except Exception as e:
            print(f"⚠️ Could not download logo: {e}")
            with open(logo_path, 'wb') as f:
                f.write(b'')
    
    return logo_path

# Try to load logo for page icon
try:
    logo_path = ensure_logo_exists()
    page_icon = Image.open(logo_path)
except:
    page_icon = "𝄞"

# Set page config with responsive settings
st.set_page_config(
    page_title="Sing Along",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --------- CONFIG: set your deployed app URL here ----------
APP_URL = "www.branks3.com"

# 🔒 SECURITY: Environment Variables for Password Hashes
ADMIN_HASH = os.getenv("ADMIN_HASH", "")
USER1_HASH = os.getenv("USER1_HASH", "")
USER2_HASH = os.getenv("USER2_HASH", "")

# Base directories
base_dir = os.getcwd()
media_dir = os.path.join(base_dir, "media")
songs_dir = os.path.join(media_dir, "songs")
lyrics_dir = os.path.join(media_dir, "lyrics_images")
logo_dir = os.path.join(media_dir, "logo")
shared_links_dir = os.path.join(media_dir, "shared_links")
metadata_path = os.path.join(media_dir, "song_metadata.json")
session_db_path = os.path.join(base_dir, "session_data.db")

# Create directories
os.makedirs(songs_dir, exist_ok=True)
os.makedirs(lyrics_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)
os.makedirs(shared_links_dir, exist_ok=True)

# =============== MOBILE DETECTION ===============
def detect_mobile():
    """Detect if user is on mobile device"""
    user_agent = st.query_params.get("user_agent", "")
    if "Mobi" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
        return True
    return False

# Initialize mobile mode
if "mobile_mode" not in st.session_state:
    st.session_state.mobile_mode = detect_mobile()

# =============== AUDIO DURATION FIX FUNCTIONS ===============
def get_audio_duration(file_path):
    """Get accurate audio duration using ffprobe (fallback to pydub if available)"""
    try:
        # Try using ffprobe first (most accurate)
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 
            'format=duration', '-of', 
            'default=noprint_wrappers=1:nokey=1', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            return duration
    except:
        pass
    
    try:
        # Fallback to pydub if installed
        from pydub import AudioSegment
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0  # Convert to seconds
    except:
        pass
    
    # Final fallback - estimate from file size
    try:
        import wave
        with wave.open(file_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return frames / float(rate)
    except:
        pass
    
    return 30.0  # Default fallback

def fix_audio_duration(input_path, output_path):
    """Fix audio duration metadata"""
    try:
        # Use ffmpeg to copy audio while ensuring proper duration
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c', 'copy',  # Copy without re-encoding
            '-map_metadata', '0',  # Copy metadata
            '-y',  # Overwrite output
            output_path
        ]
        subprocess.run(cmd, capture_output=True)
        return True
    except:
        # If ffmpeg fails, just copy the file
        import shutil
        shutil.copy2(input_path, output_path)
        return True

# =============== IMPROVED RECORDING QUALITY FUNCTIONS ===============
def create_high_quality_recording_template(song_name, original_b64, accompaniment_b64, lyrics_b64, logo_b64, song_duration):
    """Create HTML template for high-quality recording with voice clarity"""
    
    # Sanitize song name for filename
    safe_song_name = re.sub(r'[^a-zA-Z0-9_]', '_', song_name)
    
    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Sing Along - {song_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }}
        
        html, body {{
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            position: fixed;
            background: #000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        
        .container {{
            width: 100%;
            height: 100%;
            position: relative;
            background: #000;
        }}
        
        .video-container {{
            width: 100%;
            height: 100%;
            position: relative;
            overflow: hidden;
        }}
        
        .lyrics-bg {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            background: #000;
        }}
        
        .controls {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(to top, rgba(0,0,0,0.9), transparent);
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            z-index: 100;
        }}
        
        .control-buttons {{
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
        }}
        
        .control-btn {{
            background: rgba(255, 255, 255, 0.15);
            border: none;
            border-radius: 50px;
            color: white;
            padding: 12px 25px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            min-width: 140px;
            justify-content: center;
        }}
        
        .control-btn:hover {{
            background: rgba(255, 255, 255, 0.25);
            transform: translateY(-2px);
        }}
        
        .control-btn.record {{
            background: linear-gradient(135deg, #ff0066, #ff3366);
        }}
        
        .control-btn.stop {{
            background: linear-gradient(135deg, #ff3300, #ff6600);
        }}
        
        .control-btn.play {{
            background: linear-gradient(135deg, #00cc66, #33cc99);
        }}
        
        .status {{
            color: white;
            text-align: center;
            font-size: 14px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            padding: 10px;
            background: rgba(0,0,0,0.5);
            border-radius: 10px;
            margin: 0 auto;
            max-width: 300px;
        }}
        
        .back-btn {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0,0,0,0.7);
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 20px;
            cursor: pointer;
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
            backdrop-filter: blur(10px);
        }}
        
        .song-title {{
            position: absolute;
            top: 20px;
            left: 0;
            right: 0;
            text-align: center;
            color: white;
            font-size: 18px;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.8);
            padding: 10px 20px;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            backdrop-filter: blur(10px);
        }}
        
        .volume-controls {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 10px;
        }}
        
        .volume-slider {{
            width: 150px;
        }}
        
        .volume-label {{
            color: white;
            font-size: 12px;
            text-align: center;
            margin-top: 5px;
        }}
        
        /* Mobile specific styles */
        @media (max-width: 768px) {{
            .controls {{
                padding: 15px;
            }}
            
            .control-buttons {{
                flex-direction: column;
                align-items: center;
            }}
            
            .control-btn {{
                width: 90%;
                max-width: 300px;
                padding: 15px 20px;
                font-size: 14px;
            }}
            
            .back-btn {{
                top: 10px;
                left: 10px;
                width: 40px;
                height: 40px;
                font-size: 16px;
            }}
            
            .song-title {{
                top: 10px;
                font-size: 14px;
                padding: 8px 15px;
            }}
            
            .status {{
                font-size: 12px;
                padding: 8px;
            }}
            
            .volume-controls {{
                flex-direction: column;
                align-items: center;
                gap: 10px;
            }}
            
            .volume-slider {{
                width: 200px;
            }}
        }}
        
        /* Landscape mode */
        @media (orientation: landscape) and (max-height: 500px) {{
            .controls {{
                padding: 10px;
            }}
            
            .control-buttons {{
                flex-direction: row;
            }}
            
            .control-btn {{
                min-width: 120px;
                padding: 8px 15px;
                font-size: 12px;
            }}
            
            .volume-controls {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="video-container">
            <img class="lyrics-bg" src="data:image/jpeg;base64,{lyrics_b64}" alt="Lyrics Background" onerror="this.style.display='none'">
            <div class="song-title">{song_name}</div>
            <button class="back-btn" onclick="window.parent.postMessage('go_back', '*')">←</button>
        </div>
        
        <div class="controls">
            <div class="status" id="status">Ready to sing along! 🎤</div>
            <div class="control-buttons">
                <button class="control-btn play" onclick="playSong()">▶ Play Original</button>
                <button class="control-btn record" onclick="startRecording()">🎙 Start Recording</button>
                <button class="control-btn stop" onclick="stopRecording()" style="display:none;">⏹ Stop Recording</button>
            </div>
            
            <div class="volume-controls" id="volumeControls" style="display:none;">
                <div>
                    <input type="range" min="0" max="100" value="80" class="volume-slider" id="micVolume">
                    <div class="volume-label">🎤 Mic Volume</div>
                </div>
                <div>
                    <input type="range" min="0" max="100" value="30" class="volume-slider" id="musicVolume">
                    <div class="volume-label">🎵 Music Volume</div>
                </div>
            </div>
        </div>
    </div>
    
    <audio id="originalAudio" src="data:audio/mp3;base64,{original_b64}" preload="auto"></audio>
    <audio id="accompaniment" src="data:audio/mp3;base64,{accompaniment_b64}" preload="auto"></audio>
    
    <script>
        let mediaRecorder;
        let recordedChunks = [];
        let isRecording = false;
        let originalAudio = document.getElementById('originalAudio');
        let accompaniment = document.getElementById('accompaniment');
        let status = document.getElementById('status');
        let audioContext = null;
        let micStream = null;
        let destination = null;
        let micSource = null;
        let accSource = null;
        let micGain = null;
        let accGain = null;
        let compressor = null;
        let eqNode = null;
        let autoStopTimer = null;
        
        // Initialize audio context
        function initAudioContext() {{
            if (!audioContext) {{
                audioContext = new (window.AudioContext || window.webkitAudioContext)({{
                    sampleRate: 48000,
                    latencyHint: 'interactive'
                }});
            }}
            return audioContext;
        }}
        
        // Get optimized microphone stream for voice clarity
        async function getOptimizedMicrophone() {{
            try {{
                const constraints = {{
                    audio: {{
                        echoCancellation: false,  // Disable echo cancellation for better voice
                        noiseSuppression: false,  // Disable noise suppression for natural voice
                        autoGainControl: true,    // Enable auto gain
                        channelCount: 1,
                        sampleRate: 48000,        // Higher sample rate
                        sampleSize: 24,           // Higher bit depth
                        volume: 1.0
                    }},
                    video: false
                }};
                
                return await navigator.mediaDevices.getUserMedia(constraints);
            }} catch (error) {{
                // Fallback to basic constraints
                const fallbackConstraints = {{
                    audio: true,
                    video: false
                }};
                return await navigator.mediaDevices.getUserMedia(fallbackConstraints);
            }}
        }}
        
        // Create audio enhancement nodes for voice clarity
        function createAudioEnhancementNodes(ctx) {{
            // Compressor for consistent volume
            const compressor = ctx.createDynamicsCompressor();
            compressor.threshold.value = -50;
            compressor.knee.value = 40;
            compressor.ratio.value = 12;
            compressor.attack.value = 0.003;
            compressor.release.value = 0.25;
            
            // EQ for voice clarity
            const eqNode = ctx.createBiquadFilter();
            eqNode.type = 'peaking';
            eqNode.frequency.value = 2000;  // Boost around 2kHz for clarity
            eqNode.gain.value = 6;          // Moderate boost
            eqNode.Q.value = 1;
            
            // High-pass filter to remove rumble
            const highPass = ctx.createBiquadFilter();
            highPass.type = 'highpass';
            highPass.frequency.value = 80;  // Remove frequencies below 80Hz
            
            return {{ compressor, eqNode, highPass }};
        }}
        
        function playSong() {{
            if (originalAudio.paused) {{
                originalAudio.play();
                status.textContent = 'Playing original song... 🎵';
            }} else {{
                originalAudio.pause();
                originalAudio.currentTime = 0;
                status.textContent = 'Ready to sing along! 🎤';
            }}
        }}
        
        async function startRecording() {{
            try {{
                // Initialize audio context
                const ctx = initAudioContext();
                if (ctx.state === 'suspended') {{
                    await ctx.resume();
                }}
                
                status.textContent = 'Preparing recording...';
                
                // Get microphone stream
                micStream = await getOptimizedMicrophone();
                
                // Create audio nodes
                micSource = ctx.createMediaStreamSource(micStream);
                destination = ctx.createMediaStreamDestination();
                
                // Create gain nodes
                micGain = ctx.createGain();
                accGain = ctx.createGain();
                
                // Set initial volumes
                micGain.gain.value = 0.8;  // Microphone volume
                accGain.gain.value = 0.3;  // Music volume (lower so voice is clear)
                
                // Create enhancement nodes
                const enhancements = createAudioEnhancementNodes(ctx);
                compressor = enhancements.compressor;
                eqNode = enhancements.eqNode;
                const highPass = enhancements.highPass;
                
                // Connect microphone chain: mic -> gain -> highpass -> eq -> compressor -> destination
                micSource.connect(micGain);
                micGain.connect(highPass);
                highPass.connect(eqNode);
                eqNode.connect(compressor);
                compressor.connect(destination);
                
                // Load and play accompaniment
                const accResponse = await fetch(accompaniment.src);
                const accArrayBuffer = await accResponse.arrayBuffer();
                const accAudioBuffer = await ctx.decodeAudioData(accArrayBuffer);
                
                accSource = ctx.createBufferSource();
                accSource.buffer = accAudioBuffer;
                accSource.connect(accGain);
                accGain.connect(destination);
                
                // Create mixed stream (voice + music)
                const mixedStream = destination.stream;
                
                // Create MediaRecorder with high quality settings
                const options = {{
                    mimeType: 'audio/webm;codecs=opus',
                    audioBitsPerSecond: 192000  // High quality
                }};
                
                mediaRecorder = new MediaRecorder(mixedStream, options);
                recordedChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {{
                    if (event.data.size > 0) {{
                        recordedChunks.push(event.data);
                    }}
                }};
                
                mediaRecorder.onstop = () => {{
                    const blob = new Blob(recordedChunks, {{ type: 'audio/webm' }});
                    const url = URL.createObjectURL(blob);
                    
                    // Create download link
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = '{safe_song_name}_recording.webm';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    
                    status.textContent = 'Recording saved! 🎉 Downloading...';
                    
                    // Clean up
                    setTimeout(() => {{
                        URL.revokeObjectURL(url);
                        status.textContent = 'Ready for new recording! 🎤';
                    }}, 2000);
                    
                    // Clean up audio nodes
                    if (accSource) {{
                        accSource.stop();
                        accSource.disconnect();
                    }}
                    if (micSource) {{
                        micSource.disconnect();
                    }}
                    if (micStream) {{
                        micStream.getTracks().forEach(track => track.stop());
                    }}
                    
                    // Reset variables
                    accSource = null;
                    micSource = null;
                    micStream = null;
                    audioContext = null;
                }};
                
                // Start recording
                mediaRecorder.start();
                isRecording = true;
                
                // Start accompaniment
                accSource.start();
                
                // Show volume controls
                document.getElementById('volumeControls').style.display = 'flex';
                
                status.textContent = 'Recording... 🎙️ Sing along with the music!';
                
                // Setup volume controls
                document.getElementById('micVolume').addEventListener('input', (e) => {{
                    if (micGain) micGain.gain.value = e.target.value / 100;
                }});
                
                document.getElementById('musicVolume').addEventListener('input', (e) => {{
                    if (accGain) accGain.gain.value = e.target.value / 100;
                }});
                
                // Auto-stop after song duration
                autoStopTimer = setTimeout(() => {{
                    if (isRecording) {{
                        stopRecording();
                    }}
                }}, {int(song_duration * 1000)});
                
                // Update UI
                document.querySelector('.record').style.display = 'none';
                document.querySelector('.stop').style.display = 'flex';
                
            }} catch (error) {{
                console.error('Recording error:', error);
                status.textContent = 'Error: ' + error.message;
                
                if (error.name === 'NotAllowedError') {{
                    status.textContent = 'Please allow microphone access to record';
                }}
                
                // Reset UI on error
                document.querySelector('.record').style.display = 'flex';
                document.querySelector('.stop').style.display = 'none';
                document.getElementById('volumeControls').style.display = 'none';
            }}
        }}
        
        function stopRecording() {{
            if (mediaRecorder && isRecording) {{
                // Clear auto-stop timer
                if (autoStopTimer) {{
                    clearTimeout(autoStopTimer);
                    autoStopTimer = null;
                }}
                
                // Stop media recorder
                if (mediaRecorder.state !== 'inactive') {{
                    mediaRecorder.stop();
                }}
                
                // Stop accompaniment
                if (accSource) {{
                    accSource.stop();
                }}
                
                // Stop original audio if playing
                originalAudio.pause();
                originalAudio.currentTime = 0;
                
                // Hide volume controls
                document.getElementById('volumeControls').style.display = 'none';
                
                // Update UI
                isRecording = false;
                document.querySelector('.record').style.display = 'flex';
                document.querySelector('.stop').style.display = 'none';
                
                status.textContent = 'Processing recording...';
            }}
        }}
        
        // Handle back button
        window.addEventListener('message', (event) => {{
            if (event.data === 'go_back') {{
                // Stop recording if active
                if (isRecording) {{
                    stopRecording();
                }}
                window.parent.postMessage('navigate_back', '*');
            }}
        }});
        
        // Clean up on page unload
        window.addEventListener('beforeunload', () => {{
            if (isRecording) {{
                stopRecording();
            }}
            if (audioContext) {{
                audioContext.close();
            }}
        }});
        
        // Initialize on page load
        window.addEventListener('load', () => {{
            // Pre-warm audio context for better performance
            setTimeout(() => {{
                initAudioContext();
            }}, 1000);
        }});
        
        // Handle iOS/mobile audio context resume
        document.addEventListener('click', async () => {{
            if (audioContext && audioContext.state === 'suspended') {{
                await audioContext.resume();
            }}
        }}, {{ once: true }});
        
        // Handle visibility change
        document.addEventListener('visibilitychange', async () => {{
            if (document.visibilityState === 'visible' && audioContext) {{
                await audioContext.resume();
            }}
        }});
    </script>
</body>
</html>"""
    
    return template

# =============== CACHED FUNCTIONS FOR PERFORMANCE ===============
@st.cache_data(ttl=5)
def get_song_files_cached():
    """Get list of song files with caching for faster loading"""
    songs = []
    if not os.path.exists(songs_dir):
        return songs
    
    for f in os.listdir(songs_dir):
        if f.endswith("_original.mp3"):
            song_name = f.replace("_original.mp3", "")
            songs.append(song_name)
    return sorted(songs)

@st.cache_data(ttl=5)
def get_shared_links_cached():
    """Get shared links with caching"""
    return load_shared_links()

@st.cache_data(ttl=5)
def get_metadata_cached():
    """Get metadata with caching"""
    return load_metadata()

# =============== PERSISTENT SESSION DATABASE ===============
def init_session_db():
    """Initialize SQLite database for persistent sessions"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sessions
                     (session_id TEXT PRIMARY KEY,
                      user TEXT,
                      role TEXT,
                      page TEXT,
                      selected_song TEXT,
                      last_active TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS shared_links
                     (song_name TEXT PRIMARY KEY,
                      shared_by TEXT,
                      active BOOLEAN,
                      created_at TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS metadata
                     (song_name TEXT PRIMARY KEY,
                      uploaded_by TEXT,
                      timestamp REAL,
                      duration REAL)''')  # Added duration field
        conn.commit()
        conn.close()
    except:
        pass

def save_session_to_db():
    """Save current session to database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        session_id = st.session_state.get('session_id', 'default')
        
        c.execute('''INSERT OR REPLACE INTO sessions 
                     (session_id, user, role, page, selected_song, last_active)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (session_id,
                   st.session_state.get('user'),
                   st.session_state.get('role'),
                   st.session_state.get('page'),
                   st.session_state.get('selected_song'),
                   datetime.now()))
        conn.commit()
        conn.close()
    except:
        pass

def load_session_from_db():
    """Load session from database"""
    try:
        session_id = st.session_state.get('session_id', 'default')
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('SELECT user, role, page, selected_song FROM sessions WHERE session_id = ?', 
                  (session_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            user, role, page, selected_song = result
            if user and user != 'None':
                st.session_state.user = user
            if role and role != 'None':
                st.session_state.role = role
            if page and page != 'None':
                st.session_state.page = page
            if selected_song and selected_song != 'None':
                st.session_state.selected_song = selected_song
    except:
        pass

def save_shared_link_to_db(song_name, shared_by):
    """Save shared link to database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO shared_links 
                     (song_name, shared_by, active, created_at)
                     VALUES (?, ?, ?, ?)''',
                  (song_name, shared_by, True, datetime.now()))
        conn.commit()
        conn.close()
    except:
        pass

def delete_shared_link_from_db(song_name):
    """Delete shared link from database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('DELETE FROM shared_links WHERE song_name = ?', (song_name,))
        conn.commit()
        conn.close()
    except:
        pass

def load_shared_links_from_db():
    """Load shared links from database"""
    links = {}
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('SELECT song_name, shared_by FROM shared_links WHERE active = 1')
        results = c.fetchall()
        conn.close()
        
        for song_name, shared_by in results:
            links[song_name] = {"shared_by": shared_by, "active": True}
    except:
        pass
    return links

def save_metadata_to_db(song_name, uploaded_by, duration=None):
    """Save metadata to database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO metadata 
                     (song_name, uploaded_by, timestamp, duration)
                     VALUES (?, ?, ?, ?)''',
                  (song_name, uploaded_by, time.time(), duration))
        conn.commit()
        conn.close()
    except:
        pass

def delete_metadata_from_db(song_name):
    """Delete metadata from database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('DELETE FROM metadata WHERE song_name = ?', (song_name,))
        conn.commit()
        conn.close()
    except:
        pass

def load_metadata_from_db():
    """Load metadata from database"""
    metadata = {}
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('SELECT song_name, uploaded_by, duration FROM metadata')
        results = c.fetchall()
        conn.close()
        
        for song_name, uploaded_by, duration in results:
            metadata[song_name] = {
                "uploaded_by": uploaded_by, 
                "timestamp": str(time.time()),
                "duration": duration
            }
    except:
    pass
    return metadata

# Initialize database
init_session_db()

# =============== HELPER FUNCTIONS ===============
def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_metadata():
    """Load metadata from both file and database"""
    file_metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                file_metadata = json.load(f)
        except:
            file_metadata = {}
    
    db_metadata = load_metadata_from_db()
    
    # Merge, preferring database metadata
    for song_name, info in db_metadata.items():
        file_metadata[song_name] = info
    
    return file_metadata

def save_metadata(data):
    """Save metadata to both file and database"""
    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2)
    
    for song_name, info in data.items():
        uploaded_by = info.get("uploaded_by", "unknown")
        duration = info.get("duration")
        save_metadata_to_db(song_name, uploaded_by, duration)

def delete_metadata(song_name):
    """Delete metadata from both file and database"""
    metadata = load_metadata()
    
    if song_name in metadata:
        del metadata[song_name]
    
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    delete_metadata_from_db(song_name)

def load_shared_links():
    """Load shared links from both file and database"""
    file_links = {}
    if os.path.exists(shared_links_dir):
        for filename in os.listdir(shared_links_dir):
            if filename.endswith('.json'):
                song_name = filename[:-5]
                filepath = os.path.join(shared_links_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if data.get("active", True):
                            file_links[song_name] = data
                except:
                    pass
    
    db_links = load_shared_links_from_db()
    file_links.update(db_links)
    return file_links

def save_shared_link(song_name, link_data):
    """Save shared link to both file and database"""
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    with open(filepath, 'w') as f:
        json.dump(link_data, f)
    
    shared_by = link_data.get("shared_by", "unknown")
    save_shared_link_to_db(song_name, shared_by)

def delete_shared_link(song_name):
    """Delete shared link from both file and database"""
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
    
    delete_shared_link_from_db(song_name)

def get_uploaded_songs(show_unshared=False):
    """Get list of uploaded songs"""
    return get_song_files_cached()

def delete_song_files(song_name):
    """Delete all files related to a song"""
    try:
        original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
        if os.path.exists(original_path):
            os.remove(original_path)
        
        acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
        if os.path.exists(acc_path):
            os.remove(acc_path)
        
        for ext in [".jpg", ".jpeg", ".png"]:
            lyrics_path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{ext}")
            if os.path.exists(lyrics_path):
                os.remove(lyrics_path)
        
        shared_link_path = os.path.join(shared_links_dir, f"{song_name}.json")
        if os.path.exists(shared_link_path):
            os.remove(shared_link_path)
        
        get_song_files_cached.clear()
        get_shared_links_cached.clear()
        get_metadata_cached.clear()
        
        return True
    except Exception as e:
        st.error(f"Error deleting song files: {e}")
        return False

def check_and_create_session_id():
    """Create unique session ID if not exists"""
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

# =============== FAST SONG PLAYER NAVIGATION ===============
def open_song_player(song_name):
    """Fast function to open song player"""
    st.session_state.selected_song = song_name
    st.session_state.page = "Song Player"
    st.query_params["song"] = quote(song_name)
    save_session_to_db()
    st.rerun()

# =============== FIXED: QUERY PARAMETER PROCESSING ===============
def process_query_params():
    query_params = st.query_params

    if "song" in query_params:
        song_from_url = unquote(query_params["song"])

        st.session_state.selected_song = song_from_url
        st.session_state.page = "Song Player"

        if not st.session_state.get("user"):
            st.session_state.user = "guest"
            st.session_state.role = "guest"

        save_session_to_db()

# =============== GET AUDIO DURATION FOR SONG ===============
def get_song_duration(song_name):
    """Get duration for a song, calculate if not stored"""
    metadata = get_metadata_cached()
    
    if song_name in metadata and "duration" in metadata[song_name]:
        duration = metadata[song_name]["duration"]
        if duration and duration > 0:
            return duration
    
    # Calculate duration from uploaded file
    acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
    if os.path.exists(acc_path):
        try:
            duration = get_audio_duration(acc_path)
            # Store in metadata
            if song_name in metadata:
                metadata[song_name]["duration"] = duration
            else:
                metadata[song_name] = {"duration": duration, "uploaded_by": "unknown"}
            
            save_metadata(metadata)
            get_metadata_cached.clear()
            return duration
        except:
            pass
    
    return 180  # Default 3 minutes if cannot determine

# =============== RESPONSIVE CSS ===============
def apply_responsive_css():
    """Apply responsive CSS for mobile and desktop"""
    st.markdown("""
    <style>
    /* Base responsive styles */
    html, body, #root, .stApp {
        width: 100% !important;
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow-x: hidden !important;
    }
    
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
    }
    
    /* Mobile specific - 9:16 Aspect Ratio */
    @media only screen and (max-width: 768px) {
        html, body {
            overflow: hidden !important;
            position: fixed !important;
            width: 100vw !important;
            height: 100vh !important;
        }
        
        .stApp {
            max-width: 100vw !important;
            max-height: 100vh !important;
            overflow: hidden !important;
        }
        
        /* Force 9:16 aspect ratio container */
        .main .block-container {
            width: 100vw !important;
            min-height: 177.78vw !important; /* 16:9 aspect ratio */
            max-height: 100vh !important;
            padding: 0.5rem !important;
            margin: 0 auto !important;
            position: relative !important;
        }
        
        /* Adjust text sizes for mobile */
        h1 {
            font-size: 1.5rem !important;
        }
        
        h2, h3 {
            font-size: 1.2rem !important;
        }
        
        .stButton > button {
            width: 100% !important;
            margin: 0.2rem 0 !important;
            padding: 0.75rem !important;
            font-size: 1rem !important;
        }
        
        .stTextInput > div > div > input {
            font-size: 16px !important; /* Prevents zoom on iOS */
            padding: 12px !important;
        }
        
        /* Mobile columns */
        .stColumn {
            padding: 2px !important;
            margin-bottom: 5px !important;
        }
        
        /* Song player specific */
        .song-player-frame {
            width: 100vw !important;
            height: 100vh !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            border: none !important;
        }
    }
    
    /* Desktop optimization */
    @media only screen and (min-width: 769px) {
        .main .block-container {
            padding-left: 3rem !important;
            padding-right: 3rem !important;
            max-width: 1200px !important;
        }
        
        .song-player-frame {
            width: 100% !important;
            height: 700px !important;
            border: none !important;
        }
    }
    
    /* Common button styles */
    .stButton > button {
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 6px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 3px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    
    /* Fix for Streamlit elements */
    [data-testid="stSidebar"] {
        min-width: 250px !important;
        max-width: 300px !important;
    }
    
    /* Mobile song list items */
    @media only screen and (max-width: 768px) {
        .song-item {
            padding: 12px !important;
            margin: 6px 0 !important;
            border-radius: 10px !important;
            background: rgba(255,255,255,0.05) !important;
        }
    }
    
    /* Touch-friendly elements */
    @media (hover: none) and (pointer: coarse) {
        button, .stButton > button {
            min-height: 44px !important; /* Apple's recommended minimum touch target */
        }
        
        input, select, textarea {
            font-size: 16px !important; /* Prevents iOS zoom */
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Apply responsive CSS
apply_responsive_css()

# =============== INITIALIZE SESSION ===============
check_and_create_session_id()

# Initialize session state with default values
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "Login"
if "selected_song" not in st.session_state:
    st.session_state.selected_song = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None

# Load persistent session data
load_session_from_db()

# Process query parameters FIRST
process_query_params()

# Get cached metadata
metadata = get_metadata_cached()

# Logo
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
if not os.path.exists(default_logo_path):
    pass
logo_b64 = file_to_base64(default_logo_path) if os.path.exists(default_logo_path) else ""

# =============== RESPONSIVE LOGIN PAGE ===============
if st.session_state.page == "Login":
    save_session_to_db()
    
    st.markdown("""
    <style>
    /* Mobile-specific login styles */
    @media only screen and (max-width: 768px) {
        .login-container {
            width: 90% !important;
            max-width: 400px !important;
            margin: 0 auto !important;
            padding: 25px !important;
            position: relative !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
        }
        
        .login-header img {
            width: 70px !important;
            height: 70px !important;
        }
        
        .login-title {
            font-size: 1.6rem !important;
            margin: 15px 0 !important;
        }
        
        .stTextInput input {
            height: 50px !important;
            font-size: 16px !important;
        }
        
        .stButton button {
            height: 55px !important;
            font-size: 17px !important;
            font-weight: bold !important;
        }
    }
    
    /* Desktop login styles */
    @media only screen and (min-width: 769px) {
        .login-container {
            width: 400px !important;
            margin: 100px auto !important;
            padding: 40px !important;
        }
    }
    
    .login-container {
        background: rgba(15, 23, 42, 0.95) !important;
        border-radius: 20px !important;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4) !important;
        backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    .login-header {
        text-align: center !important;
        margin-bottom: 35px !important;
    }
    
    .login-header img {
        border-radius: 50% !important;
        border: 3px solid rgba(255, 255, 255, 0.3) !important;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3) !important;
    }
    
    .login-title {
        color: white !important;
        font-weight: 800 !important;
        margin: 20px 0 8px 0 !important;
        letter-spacing: 0.5px !important;
    }
    
    .login-sub {
        color: #94a3b8 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.3px !important;
    }
    
    .stTextInput input {
        background: rgba(30, 41, 59, 0.9) !important;
        border: 2px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    
    .contact-links {
        margin-top: 30px !important;
        text-align: center !important;
        padding-top: 20px !important;
        border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    .contact-link {
        display: inline-block !important;
        margin: 8px 12px !important;
        color: #94a3b8 !important;
        text-decoration: none !important;
        font-size: 0.9rem !important;
        transition: all 0.3s !important;
        padding: 6px 12px !important;
        border-radius: 6px !important;
        border: 1px solid transparent !important;
    }
    
    .contact-link:hover {
        color: white !important;
        background: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        transform: translateY(-2px) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Container for login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Login header
        st.markdown(f"""
        <div class="login-header">
            <img src="data:image/png;base64,{logo_b64}" onerror="this.style.display='none'" style="width: 90px; height: 90px;">
            <div class="login-title">𝄞 Sing Along</div>
            <div class="login-sub">Login to continue your musical journey</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Login form
        username = st.text_input("👤 Username", placeholder="Enter your username", key="login_username")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_password")
        
        # Login button
        if st.button("🎵 Login to Dashboard", type="primary", use_container_width=True):
            if not username or not password:
                st.error("❌ Please enter both username and password")
            else:
                hashed_pass = hash_password(password)
                if username == "admin" and ADMIN_HASH and hashed_pass == ADMIN_HASH:
                    st.session_state.user = username
                    st.session_state.role = "admin"
                    st.session_state.page = "Admin Dashboard"
                    st.session_state.selected_song = None
                    save_session_to_db()
                    st.rerun()
                elif username == "branks3" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.session_state.selected_song = None
                    save_session_to_db()
                    st.rerun()
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.session_state.selected_song = None
                    save_session_to_db()
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
        
        # Contact links
        st.markdown("""
        <div class="contact-links">
            <div style="color: #94a3b8; font-size: 0.85rem; margin: 0 0 15px 0; font-weight: 500;">
                Need access? Contact admin:
            </div>
            <a href="mailto:branks3.singalong@gmail.com" class="contact-link" target="_blank">
                📧 Email
            </a>
            <a href="https://www.instagram.com/branks3.sing_along/" class="contact-link" target="_blank">
                📷 Instagram
            </a>
            <a href="https://www.youtube.com/@branks3.sing_along" class="contact-link" target="_blank">
                ▶ YouTube
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    save_session_to_db()
    
    st.title(f"👑 Admin Dashboard")
    st.markdown(f"**Welcome, {st.session_state.user}**")
    
    # Mobile responsive layout
    if st.session_state.mobile_mode:
        # Mobile navigation
        page_sidebar = st.selectbox(
            "Navigate to:",
            ["Upload Songs", "Songs List", "Share Links"],
            key="admin_nav_mobile"
        )
        
        # Logout button at top
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
    else:
        # Desktop sidebar navigation
        with st.sidebar:
            page_sidebar = st.radio(
                "Navigation",
                ["Upload Songs", "Songs List", "Share Links"],
                key="admin_nav"
            )
            
            st.markdown("---")
            
            if st.button("🚪 Logout", key="admin_logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.page = "Login"
                save_session_to_db()
                st.rerun()

    # ================= UPLOAD SONGS =================
    if page_sidebar == "Upload Songs":
        st.subheader("📤 Upload New Song")
        
        with st.form("upload_form"):
            song_name_input = st.text_input(
                "🎶 Song Name",
                placeholder="Enter song name (e.g., MySong)",
                key="song_name_input"
            )
            
            # Responsive file uploaders
            if st.session_state.mobile_mode:
                uploaded_original = st.file_uploader(
                    "Original Song (_original.mp3)",
                    type=["mp3"],
                    key="original_upload",
                    help="Upload the original song file"
                )
                uploaded_accompaniment = st.file_uploader(
                    "Accompaniment (_accompaniment.mp3)",
                    type=["mp3"],
                    key="acc_upload",
                    help="Upload the accompaniment track"
                )
                uploaded_lyrics_image = st.file_uploader(
                    "Lyrics Background Image",
                    type=["jpg", "jpeg", "png"],
                    key="lyrics_upload",
                    help="Upload lyrics background image"
                )
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    uploaded_original = st.file_uploader(
                        "Original Song (_original.mp3)",
                        type=["mp3"],
                        key="original_upload"
                    )
                with col2:
                    uploaded_accompaniment = st.file_uploader(
                        "Accompaniment (_accompaniment.mp3)",
                        type=["mp3"],
                        key="acc_upload"
                    )
                with col3:
                    uploaded_lyrics_image = st.file_uploader(
                        "Lyrics Image",
                        type=["jpg", "jpeg", "png"],
                        key="lyrics_upload"
                    )
            
            submit_button = st.form_submit_button("⬆ Upload Song", type="primary", use_container_width=True)
            
            if submit_button:
                if not song_name_input:
                    st.error("❌ Please enter song name")
                elif not uploaded_original or not uploaded_accompaniment or not uploaded_lyrics_image:
                    st.error("❌ Please upload all required files")
                else:
                    song_name = song_name_input.strip()

                    original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
                    acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
                    lyrics_ext = os.path.splitext(uploaded_lyrics_image.name)[1]
                    lyrics_path = os.path.join(
                        lyrics_dir,
                        f"{song_name}_lyrics_bg{lyrics_ext}"
                    )

                    # Save files
                    with open(original_path, "wb") as f:
                        f.write(uploaded_original.getbuffer())
                    with open(acc_path, "wb") as f:
                        f.write(uploaded_accompaniment.getbuffer())
                    with open(lyrics_path, "wb") as f:
                        f.write(uploaded_lyrics_image.getbuffer())
                    
                    # Fix audio duration metadata
                    try:
                        fix_audio_duration(original_path, original_path)
                        fix_audio_duration(acc_path, acc_path)
                    except:
                        pass
                    
                    # Calculate and store duration
                    duration = get_audio_duration(acc_path)
                    
                    metadata = get_metadata_cached()
                    metadata[song_name] = {
                        "uploaded_by": st.session_state.user,
                        "timestamp": str(time.time()),
                        "duration": duration
                    }
                    save_metadata(metadata)

                    get_song_files_cached.clear()
                    get_metadata_cached.clear()

                    st.success(f"✅ Song Uploaded Successfully: {song_name}")
                    st.info(f"⏱️ Duration: {int(duration//60)}:{int(duration%60):02d}")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

    # ================= SONGS LIST =================
    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs List")
        
        # Search
        search_query = st.text_input(
            "🔍 Search songs...",
            value=st.session_state.get("search_query", ""),
            placeholder="Type song name to search",
            key="admin_search"
        )
        st.session_state.search_query = search_query
        
        uploaded_songs = get_song_files_cached()
        
        if search_query:
            uploaded_songs = [song for song in uploaded_songs 
                            if search_query.lower() in song.lower()]
        
        if not uploaded_songs:
            if search_query:
                st.warning(f"❌ No songs found matching '{search_query}'")
            else:
                st.warning("❌ No songs uploaded yet.")
        else:
            # Mobile vs desktop display
            if st.session_state.mobile_mode:
                for idx, song in enumerate(uploaded_songs):
                    duration = get_song_duration(song)
                    duration_text = f" [{int(duration//60)}:{int(duration%60):02d}]"
                    
                    # Song card for mobile
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if st.button(
                                f"🎶 {song}{duration_text}",
                                key=f"play_{song}_{idx}",
                                use_container_width=True
                            ):
                                open_song_player(song)
                        with col2:
                            # Delete button
                            if st.button("🗑️", key=f"delete_{song}_{idx}", help="Delete song"):
                                st.session_state.confirm_delete = song
                                st.rerun()
                    
                    st.markdown("---")
            else:
                # Desktop grid view
                cols_per_row = 3
                for i in range(0, len(uploaded_songs), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j in range(cols_per_row):
                        if i + j < len(uploaded_songs):
                            song = uploaded_songs[i + j]
                            duration = get_song_duration(song)
                            duration_text = f" [{int(duration//60)}:{int(duration%60):02d}]"
                            
                            with cols[j]:
                                with st.container():
                                    st.markdown(f"**{song}**{duration_text}")
                                    col_play, col_del = st.columns(2)
                                    with col_play:
                                        if st.button("🎵 Play", key=f"play_{song}_{i+j}", use_container_width=True):
                                            open_song_player(song)
                                    with col_del:
                                        if st.button("🗑️", key=f"del_{song}_{i+j}", help="Delete"):
                                            st.session_state.confirm_delete = song
                                            st.rerun()
            
            # Confirmation dialog
            if st.session_state.confirm_delete:
                song_to_delete = st.session_state.confirm_delete
                st.warning(f"⚠️ Are you sure you want to delete **{song_to_delete}**?")
                
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✅ Yes, Delete", type="primary", use_container_width=True):
                        if delete_song_files(song_to_delete):
                            delete_metadata(song_to_delete)
                            delete_shared_link(song_to_delete)
                            
                            st.success(f"✅ Song '{song_to_delete}' deleted successfully!")
                            st.session_state.confirm_delete = None
                            
                            get_song_files_cached.clear()
                            get_shared_links_cached.clear()
                            get_metadata_cached.clear()
                            
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete song '{song_to_delete}'")
                
                with col_cancel:
                    if st.button("❌ Cancel", type="secondary", use_container_width=True):
                        st.session_state.confirm_delete = None
                        st.rerun()

    # ================= SHARE LINKS =================
    elif page_sidebar == "Share Links":
        st.subheader("🔗 Manage Shared Links")
        
        all_songs = get_song_files_cached()
        
        # Search
        search_query = st.text_input(
            "🔍 Search songs...",
            value=st.session_state.get("search_query", ""),
            placeholder="Type song name to search",
            key="share_search"
        )
        st.session_state.search_query = search_query
        
        if search_query:
            all_songs = [song for song in all_songs 
                        if search_query.lower() in song.lower()]
        
        shared_links_data = get_shared_links_cached()

        if not all_songs:
            if search_query:
                st.warning(f"❌ No songs found matching '{search_query}'")
            else:
                st.warning("❌ No songs available to share.")
        else:
            # Mobile vs desktop display
            if st.session_state.mobile_mode:
                for song in all_songs:
                    safe_song = quote(song)
                    is_shared = song in shared_links_data
                    status = "✅ SHARED" if is_shared else "❌ NOT SHARED"
                    
                    with st.container():
                        st.markdown(f"**{song}** - {status}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if is_shared:
                                if st.button("🚫 Unshare", key=f"unshare_{song}", use_container_width=True):
                                    delete_shared_link(song)
                                    get_shared_links_cached.clear()
                                    st.success(f"✅ {song} unshared!")
                                    time.sleep(0.5)
                                    st.rerun()
                            else:
                                if st.button("🔗 Share", key=f"share_{song}", use_container_width=True):
                                    save_shared_link(
                                        song,
                                        {"shared_by": st.session_state.user, "active": True}
                                    )
                                    get_shared_links_cached.clear()
                                    share_url = f"{APP_URL}?song={safe_song}"
                                    st.success(f"✅ {song} shared!")
                                    time.sleep(0.5)
                                    st.rerun()
                        
                        with col2:
                            if is_shared:
                                share_url = f"{APP_URL}?song={safe_song}"
                                if st.button("📋 Copy Link", key=f"copy_{song}", use_container_width=True):
                                    st.code(share_url, language=None)
                                    st.success("Link copied to clipboard!")
                        
                        st.markdown("---")
            else:
                # Desktop table view
                for song in all_songs:
                    col1, col2, col3 = st.columns([3, 2, 2])
                    
                    with col1:
                        safe_song = quote(song)
                        is_shared = song in shared_links_data
                        status = "✅ SHARED" if is_shared else "❌ NOT SHARED"
                        st.write(f"**{song}** - {status}")
                    
                    with col2:
                        if is_shared:
                            if st.button("🚫 Unshare", key=f"unshare_{song}", use_container_width=True):
                                delete_shared_link(song)
                                get_shared_links_cached.clear()
                                st.success(f"✅ {song} unshared!")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            if st.button("🔗 Share", key=f"share_{song}", use_container_width=True):
                                save_shared_link(
                                    song,
                                    {"shared_by": st.session_state.user, "active": True}
                                )
                                get_shared_links_cached.clear()
                                share_url = f"{APP_URL}?song={safe_song}"
                                st.success(f"✅ {song} shared!")
                                time.sleep(0.5)
                                st.rerun()
                    
                    with col3:
                        if is_shared:
                            share_url = f"{APP_URL}?song={safe_song}"
                            if st.button("📋 Copy Link", key=f"copy_{song}", use_container_width=True):
                                st.code(share_url, language=None)
                                st.success("Link copied to clipboard!")

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    save_session_to_db()
    
    st.title(f"🎵 User Dashboard")
    st.markdown(f"**Welcome, {st.session_state.user}**")
    
    # Mobile responsive sidebar
    if st.session_state.mobile_mode:
        # Mobile controls at top
        col_refresh, col_logout = st.columns(2)
        with col_refresh:
            if st.button("🔄 Refresh", use_container_width=True):
                get_song_files_cached.clear()
                get_shared_links_cached.clear()
                st.rerun()
        with col_logout:
            if st.button("🚪 Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.page = "Login"
                save_session_to_db()
                st.rerun()
    else:
        # Desktop sidebar
        with st.sidebar:
            st.markdown("### 🎵 Quick Actions")
            
            if st.button("🔄 Refresh Songs List", use_container_width=True):
                get_song_files_cached.clear()
                get_shared_links_cached.clear()
                st.rerun()
            
            if st.button("🚪 Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.page = "Login"
                save_session_to_db()
                st.rerun()

    st.subheader("🎶 Available Songs")
    
    # Search
    search_query = st.text_input(
        "🔍 Search songs...",
        value=st.session_state.get("search_query", ""),
        placeholder="Type song name to search",
        key="user_search"
    )
    st.session_state.search_query = search_query
    
    all_songs = get_song_files_cached()
    shared_links = get_shared_links_cached()
    
    uploaded_songs = [song for song in all_songs if song in shared_links]
    
    if search_query:
        uploaded_songs = [song for song in uploaded_songs 
                         if search_query.lower() in song.lower()]

    if not uploaded_songs:
        if search_query:
            st.warning(f"❌ No songs found matching '{search_query}'")
        else:
            st.warning("❌ No shared songs available. Contact admin to share songs.")
            st.info("👑 Only admin-shared songs appear here for users.")
    else:
        # Mobile vs desktop display
        if st.session_state.mobile_mode:
            # Mobile grid with 2 columns
            cols = st.columns(2)
            for idx, song in enumerate(uploaded_songs):
                duration = get_song_duration(song)
                duration_text = f" {int(duration//60)}:{int(duration%60):02d}"
                
                with cols[idx % 2]:
                    if st.button(
                        f"🎵 {song[:15]}{'...' if len(song) > 15 else ''}\n⏱️{duration_text}",
                        key=f"user_song_{song}_{idx}",
                        use_container_width=True,
                        type="primary"
                    ):
                        open_song_player(song)
        else:
            # Desktop list
            for idx, song in enumerate(uploaded_songs):
                duration = get_song_duration(song)
                duration_text = f" [{int(duration//60)}:{int(duration%60):02d}]"
                
                if st.button(
                    f"🎵 {song}{duration_text}",
                    key=f"user_song_{song}_{idx}",
                    help="Click to play song",
                    use_container_width=True,
                    type="secondary"
                ):
                    open_song_player(song)

# =============== SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    save_session_to_db()
    
    selected_song = st.session_state.get("selected_song", None)
    if not selected_song:
        st.error("No song selected!")
        if st.session_state.role in ["admin", "user"]:
            if st.button("Go Back"):
                if st.session_state.role == "admin":
                    st.session_state.page = "Admin Dashboard"
                elif st.session_state.role == "user":
                    st.session_state.page = "User Dashboard"
                save_session_to_db()
                st.rerun()
        st.stop()

    shared_links = get_shared_links_cached()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"
    came_from_dashboard = st.session_state.role in ["admin", "user"]

    if not (is_admin or came_from_dashboard or is_shared):
        st.error("❌ Access denied!")
        st.stop()

    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")

    lyrics_path = ""
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}")
        if os.path.exists(p):
            lyrics_path = p
            break

    original_b64 = file_to_base64(original_path)
    accompaniment_b64 = file_to_base64(accompaniment_path)
    lyrics_b64 = file_to_base64(lyrics_path)
    
    # Get accurate duration from uploaded file
    song_duration = get_song_duration(selected_song)
    
    # Create high-quality recording template
    karaoke_html = create_high_quality_recording_template(
        selected_song,
        original_b64,
        accompaniment_b64,
        lyrics_b64,
        logo_b64,
        song_duration
    )
    
    # Display the song player
    st.markdown('<div class="song-player-container">', unsafe_allow_html=True)
    
    # Back button
    if st.session_state.role in ["admin", "user"]:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("← Back", use_container_width=True, type="secondary"):
                if st.session_state.role == "admin":
                    st.session_state.page = "Admin Dashboard"
                elif st.session_state.role == "user":
                    st.session_state.page = "User Dashboard"
                st.session_state.selected_song = None
                
                if "song" in st.query_params:
                    del st.query_params["song"]
                
                save_session_to_db()
                st.rerun()
    
    # Display the karaoke player
    html(karaoke_html, height=700 if st.session_state.mobile_mode else 800, scrolling=False)

# =============== FALLBACK ===============
else:
    if "song" in st.query_params:
        st.session_state.page = "Song Player"
    else:
        st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()
