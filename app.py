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
import numpy as np
st.text("google.com, pub-2373888797323762, DIRECT, f08c47fec0942fa0")
# =============== ADD GOOGLE ADSENSE VERIFICATION CODE ===============
st.markdown("""
<meta name="google-adsense-account" content="ca-pub-2373888797323762">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2373888797323762"
     crossorigin="anonymous"></script>
""", unsafe_allow_html=True)

# =============== RESPONSIVE FIXES ===============
st.markdown("""
<style>
/* Force mobile view for all devices */
@media only screen and (min-width: 769px) {
    .main .block-container {
        max-width: 360px !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    .stApp {
        width: 360px !important;
        margin: 0 auto !important;
        border-left: 1px solid #ddd;
        border-right: 1px solid #ddd;
        min-height: 100vh;
        position: relative;
    }
}

/* Mobile optimization */
@media only screen and (max-width: 768px) {
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        width: 100% !important;
        max-width: 100% !important;
    }
    
    .stApp {
        min-height: 100vh !important;
    }
}

/* Force 9:16 aspect ratio for karaoke player */
.karaoke-container {
    aspect-ratio: 9/16 !important;
    width: 100% !important;
    max-width: 360px !important;
    margin: 0 auto !important;
    position: relative !important;
    background: #000 !important;
}

html, body, #root, .stApp {
    min-height: 100vh !important;
}

/* Remove all scrolling */
[data-testid="stAppViewContainer"] {
    overflow: hidden !important;
}

.stApp {
    overflow: hidden !important;
}

/* Mobile specific fixes */
@media (max-width: 768px) {
    .stButton > button {
        width: 100% !important;
        margin: 4px 0 !important;
    }
    
    .stTextInput > div > div > input {
        font-size: 16px !important;
    }
    
    [data-testid="stSidebar"] {
        min-width: 200px !important;
        max-width: 80% !important;
    }
}
</style>
""", unsafe_allow_html=True)

# =============== LOGO DOWNLOAD AND LOADING ===============
def ensure_logo_exists():
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

# Set page config
st.set_page_config(
    page_title="Sing Along",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --------- CONFIG: set your deployed app URL here ----------
APP_URL = "www.branks3.com"

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

# =============== IMPROVED ACCURATE AUDIO DURATION FUNCTIONS ===============
def get_audio_duration(file_path):
    """Get accurate audio duration using multiple methods"""
    if not os.path.exists(file_path):
        return None
    
    methods_tried = []
    
    # Method 1: ffprobe (most accurate)
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 
            'format=duration', '-of', 
            'default=noprint_wrappers=1:nokey=1', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            if duration > 0:
                print(f"✅ ffprobe duration for {os.path.basename(file_path)}: {duration}")
                return duration
        methods_tried.append("ffprobe")
    except Exception as e:
        methods_tried.append(f"ffprobe failed: {str(e)[:50]}")
    
    # Method 2: mutagen (if installed) - pure Python MP3 metadata
    try:
        from mutagen.mp3 import MP3
        audio = MP3(file_path)
        duration = audio.info.length
        if duration > 0:
            print(f"✅ mutagen duration for {os.path.basename(file_path)}: {duration}")
            return duration
        methods_tried.append("mutagen")
    except Exception as e:
        methods_tried.append(f"mutagen failed: {str(e)[:50]}")
    
    # Method 3: pydub (if installed)
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(file_path)
        duration = len(audio) / 1000.0
        if duration > 0:
            print(f"✅ pydub duration for {os.path.basename(file_path)}: {duration}")
            return duration
        methods_tried.append("pydub")
    except Exception as e:
        methods_tried.append(f"pydub failed: {str(e)[:50]}")
    
    # Method 4: wave module for WAV files
    try:
        import wave
        if file_path.lower().endswith('.wav'):
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = frames / float(rate)
                if duration > 0:
                    print(f"✅ wave duration for {os.path.basename(file_path)}: {duration}")
                    return duration
    except Exception as e:
        methods_tried.append(f"wave failed: {str(e)[:50]}")
    
    # Method 5: File size estimation for MP3 (last resort)
    try:
        if file_path.lower().endswith('.mp3'):
            # More accurate estimation: 128kbps = 0.94 MB per minute
            file_size = os.path.getsize(file_path)
            # Convert bytes to bits: *8, convert kbps to bps: *1024
            estimated_duration = (file_size * 8) / (128 * 1024)  # Convert to seconds
            if estimated_duration > 0:
                print(f"⚠️ Estimated duration for {os.path.basename(file_path)}: {estimated_duration}")
                return estimated_duration
    except Exception as e:
        methods_tried.append(f"size estimation failed: {str(e)[:50]}")
    
    print(f"❌ All methods failed for {os.path.basename(file_path)}: {methods_tried}")
    return None

def fix_audio_duration(input_path, output_path):
    """Fix audio duration metadata"""
    try:
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c', 'copy',
            '-map_metadata', '0',
            '-y',
            output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=15)
        return True
    except Exception as e:
        print(f"Warning: Could not fix audio duration: {e}")
        import shutil
        shutil.copy2(input_path, output_path)
        return True

# =============== HIGH QUALITY AUDIO PROCESSING ===============
def process_audio_for_quality(input_path, output_path):
    """Process audio for better quality and fix duration issues"""
    try:
        # Use ffmpeg to process audio with optimal settings
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:a', 'libmp3lame',
            '-q:a', '0',  # Highest quality (0-9, 0 is best)
            '-ar', '48000',  # High sample rate
            '-b:a', '320k',  # High bitrate
            '-map_metadata', '0',
            '-id3v2_version', '3',
            '-write_xing', '0',  # Fix duration issues
            '-y',
            output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=20)
        
        # Verify duration after processing
        duration = get_audio_duration(output_path)
        print(f"✅ Processed audio duration: {duration} seconds")
        return True
    except Exception as e:
        print(f"⚠️ Audio processing failed, using original: {e}")
        import shutil
        shutil.copy2(input_path, output_path)
        return True

# =============== CACHED FUNCTIONS FOR PERFORMANCE ===============
@st.cache_data(ttl=5)
def get_song_files_cached():
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
    return load_shared_links()

@st.cache_data(ttl=5)
def get_metadata_cached():
    return load_metadata()

# =============== PERSISTENT SESSION DATABASE ===============
def init_session_db():
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
                      duration REAL,
                      processed BOOLEAN DEFAULT 0)''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database init error: {e}")

def save_session_to_db():
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
    except Exception as e:
        print(f"Save session error: {e}")

def load_session_from_db():
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
    except Exception as e:
        print(f"Load session error: {e}")

def save_shared_link_to_db(song_name, shared_by):
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO shared_links 
                     (song_name, shared_by, active, created_at)
                     VALUES (?, ?, ?, ?)''',
                  (song_name, shared_by, True, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Save shared link error: {e}")

def delete_shared_link_from_db(song_name):
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('DELETE FROM shared_links WHERE song_name = ?', (song_name,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Delete shared link error: {e}")

def load_shared_links_from_db():
    links = {}
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('SELECT song_name, shared_by FROM shared_links WHERE active = 1')
        results = c.fetchall()
        conn.close()
        
        for song_name, shared_by in results:
            links[song_name] = {"shared_by": shared_by, "active": True}
    except Exception as e:
        print(f"Load shared links error: {e}")
    return links

def save_metadata_to_db(song_name, uploaded_by, duration=None, processed=False):
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO metadata 
                     (song_name, uploaded_by, timestamp, duration, processed)
                     VALUES (?, ?, ?, ?, ?)''',
                  (song_name, uploaded_by, time.time(), duration, processed))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Save metadata error: {e}")

def delete_metadata_from_db(song_name):
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('DELETE FROM metadata WHERE song_name = ?', (song_name,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Delete metadata error: {e}")

def load_metadata_from_db():
    metadata = {}
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('SELECT song_name, uploaded_by, duration, processed FROM metadata')
        results = c.fetchall()
        conn.close()
        
        for song_name, uploaded_by, duration, processed in results:
            metadata[song_name] = {
                "uploaded_by": uploaded_by, 
                "timestamp": str(time.time()),
                "duration": duration,
                "processed": bool(processed)
            }
    except Exception as e:
        print(f"Load metadata error: {e}")
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
    file_metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                file_metadata = json.load(f)
        except:
            file_metadata = {}
    
    db_metadata = load_metadata_from_db()
    for song_name, info in db_metadata.items():
        file_metadata[song_name] = info
    
    return file_metadata

def save_metadata(data):
    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2)
    
    for song_name, info in data.items():
        uploaded_by = info.get("uploaded_by", "unknown")
        duration = info.get("duration")
        processed = info.get("processed", False)
        save_metadata_to_db(song_name, uploaded_by, duration, processed)

def delete_metadata(song_name):
    metadata = load_metadata()
    
    if song_name in metadata:
        del metadata[song_name]
    
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    delete_metadata_from_db(song_name)

def load_shared_links():
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
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    with open(filepath, 'w') as f:
        json.dump(link_data, f)
    
    shared_by = link_data.get("shared_by", "unknown")
    save_shared_link_to_db(song_name, shared_by)

def delete_shared_link(song_name):
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
    
    delete_shared_link_from_db(song_name)

def get_uploaded_songs(show_unshared=False):
    return get_song_files_cached()

def delete_song_files(song_name):
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
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())

# =============== FAST SONG PLAYER NAVIGATION ===============
def open_song_player(song_name):
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

# =============== IMPROVED GET ACCURATE AUDIO DURATION FOR SONG ===============
def get_song_duration(song_name):
    """Get accurate duration for a song"""
    metadata = get_metadata_cached()
    
    # Check if we have stored duration in metadata
    if song_name in metadata and "duration" in metadata[song_name]:
        stored_duration = metadata[song_name]["duration"]
        if stored_duration and stored_duration > 0:
            print(f"✅ Using stored duration for {song_name}: {stored_duration}")
            return stored_duration
    
    # Try processed accompaniment file first
    acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
    if os.path.exists(acc_path):
        try:
            duration = get_audio_duration(acc_path)
            if duration and duration > 0:
                # Store in metadata
                if song_name in metadata:
                    metadata[song_name]["duration"] = duration
                else:
                    metadata[song_name] = {"duration": duration, "uploaded_by": "unknown"}
                
                save_metadata(metadata)
                get_metadata_cached.clear()
                print(f"✅ Calculated accompaniment duration for {song_name}: {duration}")
                return duration
        except Exception as e:
            print(f"⚠️ Failed to get accompaniment duration for {song_name}: {e}")
    
    # Try original file as fallback
    original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
    if os.path.exists(original_path):
        try:
            duration = get_audio_duration(original_path)
            if duration and duration > 0:
                print(f"✅ Calculated original duration for {song_name}: {duration}")
                return duration
        except Exception as e:
            print(f"⚠️ Failed to get original duration for {song_name}: {e}")
    
    # If we can't determine duration, try to estimate from file size
    if os.path.exists(acc_path):
        try:
            file_size = os.path.getsize(acc_path)
            # Better estimation: MP3 at 128kbps
            estimated_duration = (file_size * 8) / (128 * 1024)
            if estimated_duration > 30:
                print(f"⚠️ Estimated duration from file size for {song_name}: {estimated_duration}")
                return estimated_duration
        except:
            pass
    
    # Return reasonable default
    print(f"⚠️ Using default duration for {song_name}")
    return 180

def ensure_audio_processed(song_name):
    """Ensure audio files are processed for high quality"""
    metadata = get_metadata_cached()
    
    if song_name in metadata and metadata[song_name].get("processed", False):
        return True
    
    original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
    acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
    
    # Create processed versions
    processed_original = os.path.join(songs_dir, f"{song_name}_original_processed.mp3")
    processed_acc = os.path.join(songs_dir, f"{song_name}_accompaniment_processed.mp3")
    
    try:
        # Process both files
        print(f"🔧 Processing audio for {song_name}...")
        process_audio_for_quality(original_path, processed_original)
        process_audio_for_quality(acc_path, processed_acc)
        
        # Update metadata
        if song_name in metadata:
            metadata[song_name]["processed"] = True
        else:
            metadata[song_name] = {"processed": True, "uploaded_by": "unknown"}
        
        save_metadata(metadata)
        get_metadata_cached.clear()
        print(f"✅ Audio processed for {song_name}")
        return True
    except Exception as e:
        print(f"⚠️ Audio processing failed for {song_name}: {e}")
        return False

# =============== INITIALIZE SESSION ===============
check_and_create_session_id()

# Initialize session state with default values
if "user" not in st.session_state:
    st.session_state.user = "guest"
if "role" not in st.session_state:
    st.session_state.role = "guest"
if "page" not in st.session_state:
    st.session_state.page = "User Dashboard"  # Changed from Login to User Dashboard
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

# =============== REMOVED LOGIN PAGE - DIRECT TO USER DASHBOARD ===============
# =============== USER DASHBOARD (FOR ALL USERS) ===============
if st.session_state.page == "User Dashboard":
    save_session_to_db()
    
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        h3 {
            font-size: 1.2rem !important;
        }
        
        [data-testid="stSidebar"] h2 {
            font-size: 1.3rem !important;
        }
        
        [data-testid="stSidebar"] h3 {
            font-size: 1.1rem !important;
        }
        
        .stButton > button {
            font-size: 14px !important;
            padding: 8px 12px !important;
        }
        
        .user-song-name {
            font-size: 14px !important;
        }
        
        .stTextInput > div > div > input {
            font-size: 14px !important;
            padding: 8px !important;
        }
        
        [data-testid="stSidebar"] {
            min-width: 200px !important;
            max-width: 250px !important;
        }
        
        .main .block-container {
            padding: 1rem !important;
        }
    }
    
    @media (max-width: 480px) {
        h3 {
            font-size: 1.1rem !important;
        }
        
        .stButton > button {
            font-size: 12px !important;
            padding: 6px 10px !important;
        }
        
        .stTextInput > div > div > input {
            font-size: 12px !important;
            padding: 6px !important;
        }
        
        [data-testid="stSidebar"] {
            min-width: 180px !important;
            max-width: 220px !important;
        }
        
        [data-testid="stSidebar"] h2 {
            font-size: 1.2rem !important;
        }
    }
    
    .clickable-song {
        cursor: pointer;
        padding: 12px 8px;
        transition: all 0.2s ease;
        border-radius: 0px;
        background: transparent !important;
        border: none !important;
        text-align: left;
        width: 100%;
        display: block;
        margin: 0 !important;
    }
    
    .clickable-song:hover {
        background: rgba(255, 0, 102, 0.1) !important;
        transform: translateX(5px);
    }
    
    @media (max-width: 768px) {
        .clickable-song {
            padding: 10px 6px;
            margin-bottom: 5px !important;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
    }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>🎵 Sing Along</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown("### Quick Actions")
        
        if st.button("🔄 Refresh Songs List", key="user_refresh"):
            get_song_files_cached.clear()
            get_shared_links_cached.clear()
            st.rerun()

    st.subheader("🎵 Available Songs")
    
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
            st.warning("❌ No shared songs available.")
    else:
        for idx, song in enumerate(uploaded_songs):
            # Display song with duration
            duration = get_song_duration(song)
            if duration:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                display_name = f"✅ *{song}*"
            else:
                display_name = f"✅ *{song}*"
            
            if st.button(
                display_name,
                key=f"user_song_{song}_{idx}",
                help="Click to play song",
                use_container_width=True,
                type="secondary"
            ):
                open_song_player(song)

# =============== SONG PLAYER WITH FIXED ISSUES ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    save_session_to_db()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    header {visibility: hidden !important;}
    .st-emotion-cache-1pahdxg {display:none !important;}
    .st-emotion-cache-18ni7ap {padding: 0 !important;}
    footer {visibility: hidden !important;}
    div.block-container {
        padding: 0 !important;
        margin: 0 auto !important;
        width: 360px !important;
        max-width: 360px !important;
        overflow: hidden !important;
        aspect-ratio: 9/16 !important;
        position: relative !important;
    }
    html, body {
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        height: 100vh !important;
    }
    #root > div > div > div > div > section > div {padding-top: 0rem !important;}
    .stApp {
        overflow: hidden !important;
        width: 100% !important;
        height: 100vh !important;
        margin: 0 auto !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    
    /* Mobile specific */
    @media (max-width: 768px) {
        div.block-container {
            width: 100% !important;
            max-width: 100% !important;
            height: 100vh !important;
        }
        
        .stButton > button[kind="secondary"] {
            font-size: 14px !important;
            padding: 8px 12px !important;
            margin: 5px !important;
        }
    }
    
    /* Desktop: force 9:16 aspect ratio */
    @media (min-width: 769px) {
        div.block-container {
            width: 360px !important;
            height: 640px !important;
            margin: 20px auto !important;
            border: 1px solid #ddd;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .stApp {
            background: #f0f0f0 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    selected_song = st.session_state.get("selected_song", None)
    if not selected_song:
        st.error("No song selected!")
        if st.session_state.role in ["admin", "user"]:
            if st.button("Go Back"):
                if st.session_state.role == "admin":
                    st.session_state.page = "Admin Dashboard"
                    st.session_state.selected_song = None
                elif st.session_state.role == "user":
                    st.session_state.page = "User Dashboard"
                    st.session_state.selected_song = None
                
                if "song" in st.query_params:
                    del st.query_params["song"]
                
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

    # Check for processed audio files first
    processed_original_path = os.path.join(songs_dir, f"{selected_song}_original_processed.mp3")
    processed_accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment_processed.mp3")
    
    # Use processed files if available, otherwise use original
    if os.path.exists(processed_original_path):
        original_path = processed_original_path
    else:
        original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    
    if os.path.exists(processed_accompaniment_path):
        accompaniment_path = processed_accompaniment_path
    else:
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
    
    song_duration = get_song_duration(selected_song)
    if not song_duration or song_duration <= 0:
        song_duration = 180

    # ✅ FIXED KARAOKE TEMPLATE - PLAYBACK IN SAME INTERFACE
    karaoke_template = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>🎤 Sing Along</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <style>
  * { 
      margin: 0; 
      padding: 0; 
      box-sizing: border-box; 
      -webkit-tap-highlight-color: transparent;
  }
  html, body {
      overflow: hidden !important;
      width: 100% !important;
      height: 100% !important;
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      background: #000 !important;
      touch-action: manipulation;
  }
  body { 
      background: #000; 
      font-family: 'Poppins', sans-serif; 
      height: 100% !important;
      width: 100% !important;
      overflow: hidden !important;
      position: fixed !important;
      margin: 0 !important;
      padding: 0 !important;
  }
  .karaoke-wrapper {
      width: 100% !important;
      height: 100% !important;
      position: absolute !important;
      top: 0 !important;
      left: 0 !important;
      background: #111 !important;
      overflow: hidden !important;
      aspect-ratio: 9/16 !important;
  }
  #status { 
      position: absolute; 
      top: 10px; 
      width: 100%; 
      text-align: center; 
      font-size: 12px; 
      color: #ccc; 
      z-index: 20; 
      text-shadow: 1px 1px 6px rgba(0,0,0,0.9); 
      padding: 5px;
  }
  .reel-bg { 
      position: absolute; 
      top: 0; 
      left: 0; 
      width: 100% !important; 
      height: 75% !important; 
      object-fit: contain !important;
      object-position: center !important;
  }
  .lyrics { 
      position: absolute; 
      bottom: 30%; 
      width: 100%; 
      text-align: center; 
      font-size: 4vw; 
      font-weight: bold; 
      color: white; 
      text-shadow: 2px 2px 10px black; 
      padding: 0 10px;
  }
  .controls { 
      position: absolute; 
      bottom: 10%; 
      width: 100%; 
      text-align: center; 
      z-index: 30; 
      display: flex;
      justify-content: center;
      flex-wrap: wrap;
      gap: 5px;
      padding: 0 10px;
  }
  button { 
      background: linear-gradient(135deg, #ff0066, #ff66cc); 
      border: none; 
      color: white; 
      padding: 10px 15px; 
      border-radius: 20px; 
      font-size: 12px; 
      margin: 2px; 
      box-shadow: 0px 3px 15px rgba(255,0,128,0.4); 
      cursor: pointer; 
      min-width: 100px;
      flex: 1;
      max-width: 150px;
      -webkit-appearance: none;
      -moz-appearance: none;
      appearance: none;
  }
  button:active { 
      transform: scale(0.95); 
      opacity: 0.9;
  }
  .final-output { 
      position: absolute !important; 
      width: 100% !important; 
      height: 100% !important; 
      top: 0 !important; 
      left: 0 !important; 
      background: rgba(0,0,0,0.95); 
      display: none; 
      justify-content: center; 
      align-items: center; 
      z-index: 999; 
  }
  #logoImg { 
      position: absolute; 
      top: 10px; 
      left: 10px; 
      width: 30px;
      height: 30px;
      z-index: 50; 
      opacity: 1;
      filter: brightness(1.2);
  }
  canvas { 
      display: none; 
  }
  .audio-player {
      display: none;
  }
  /* Recording playback video */
  #recordingVideoPlayer {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: contain;
      background: #000;
      display: none;
      z-index: 1000;
  }
  /* Video controls overlay */
  .video-controls {
      position: absolute;
      bottom: 10%;
      width: 100%;
      text-align: center;
      z-index: 1001;
      display: flex;
      justify-content: center;
      gap: 10px;
  }
  .video-controls button {
      background: rgba(0,0,0,0.7);
      border: 1px solid rgba(255,255,255,0.3);
  }
  </style>
</head>
<body>
  <div class="karaoke-wrapper" id="karaokeWrapper">
      <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%" onerror="this.style.display='none'">
      <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%" onerror="this.style.display='none'">
      <div id="status">Ready 🎤 Tap screen first</div>
      
      <!-- Audio elements - hidden -->
      <audio id="originalAudio" class="audio-player" preload="auto" data-src="data:audio/mp3;base64,%%ORIGINAL_B64%%"></audio>
      <audio id="accompaniment" class="audio-player" preload="auto" data-src="data:audio/mp3;base64,%%ACCOMP_B64%%"></audio>
      
      <div class="controls">
        <button id="playBtn">▶ Play Original</button>
        <button id="recordBtn">🎙 Start Recording</button>
        <button id="stopBtn" style="display:none;">⏹ Stop Recording</button>
      </div>
  </div>

  <div class="final-output" id="finalOutputDiv">
    <div class="karaoke-wrapper">
      <img class="reel-bg" id="finalBg">
      <div id="finalStatus">Recording Complete!</div>
      <div class="controls">
        <button id="playRecordingBtn">▶ Play</button>
        <a id="downloadRecordingBtn" href="#" download>
          <button>⬇ Download</button>
        </a>
        <button id="newRecordingBtn">New</button>
      </div>
    </div>
  </div>

  <!-- Video player for recording playback -->
  <video id="recordingVideoPlayer" controls></video>
  <div class="video-controls" id="videoControls" style="display:none;">
    <button onclick="closeVideoPlayer()">Close</button>
    <button onclick="toggleFullscreen()">Fullscreen</button>
  </div>

  <canvas id="recordingCanvas"></canvas>

  <script>
  /* ================== GLOBAL STATE ================== */
  let mediaRecorder;
  let recordedChunks = [];
  let playRecordingAudio = null;
  let lastRecordingURL = null;
  let audioContext, micSource, accSource, micGain, accGain, destination, originalSource;
  let canvasRafId = null;
  let isRecording = false;
  let isPlayingRecording = false;
  let autoStopTimer = null;
  let isSongPlaying = false;
  let micStream = null;
  let recordingStartTime = 0;
  let recordingDuration = 0;
  let originalAudioBuffer = null;
  let accompanimentBuffer = null;

  /* ================== ELEMENTS ================== */
  const playBtn = document.getElementById("playBtn");
  const recordBtn = document.getElementById("recordBtn");
  const stopBtn = document.getElementById("stopBtn");
  const status = document.getElementById("status");
  const originalAudio = document.getElementById("originalAudio");
  const accompanimentAudio = document.getElementById("accompaniment");
  const finalDiv = document.getElementById("finalOutputDiv");
  const mainBg = document.getElementById("mainBg");
  const finalBg = document.getElementById("finalBg");
  const finalStatus = document.getElementById("finalStatus");
  const playRecordingBtn = document.getElementById("playRecordingBtn");
  const downloadRecordingBtn = document.getElementById("downloadRecordingBtn");
  const newRecordingBtn = document.getElementById("newRecordingBtn");
  const canvas = document.getElementById("recordingCanvas");
  const ctx = canvas.getContext("2d");
  const logoImg = new Image();
  logoImg.src = document.getElementById("logoImg").src;
  const recordingVideoPlayer = document.getElementById("recordingVideoPlayer");
  const videoControls = document.getElementById("videoControls");

  /* ================== CANVAS SETUP ================== */
  canvas.width = 720;
  canvas.height = 1280;

  /* ================== AUDIO CONTEXT FIX ================== */
  async function ensureAudioContext() {
      if (!audioContext) {
          audioContext = new (window.AudioContext || window.webkitAudioContext)({
              sampleRate: 48000,
              latencyHint: 'playback'
          });
      }
      if (audioContext.state === "suspended") {
          await audioContext.resume();
      }
      return audioContext;
  }

  /* ================== LOAD AUDIO BUFFERS ================== */
  async function loadAudioBuffers() {
      const audioCtx = await ensureAudioContext();
      
      // Load original song
      const originalRes = await fetch(originalAudio.getAttribute('data-src'));
      const originalArrayBuffer = await originalRes.arrayBuffer();
      originalAudioBuffer = await audioCtx.decodeAudioData(originalArrayBuffer);
      
      // Load accompaniment
      const accRes = await fetch(accompanimentAudio.getAttribute('data-src'));
      const accArrayBuffer = await accRes.arrayBuffer();
      accompanimentBuffer = await audioCtx.decodeAudioData(accArrayBuffer);
      
      console.log("✅ Audio buffers loaded:");
      console.log("- Original duration:", originalAudioBuffer.duration);
      console.log("- Accompaniment duration:", accompanimentBuffer.duration);
  }

  /* ================== PLAY/STOP ORIGINAL SONG ================== */
  playBtn.onclick = async function() {
      await ensureAudioContext();
      
      if (!originalAudioBuffer) {
          await loadAudioBuffers();
      }
      
      if (!isSongPlaying) {
          // Create and play original song buffer
          originalSource = audioContext.createBufferSource();
          originalSource.buffer = originalAudioBuffer;
          originalSource.connect(audioContext.destination);
          originalSource.start();
          
          isSongPlaying = true;
          playBtn.innerText = "⏹ Stop Original";
          status.innerText = "🎵 Playing original song...";
          
          // Auto stop when song ends
          originalSource.onended = () => {
              isSongPlaying = false;
              playBtn.innerText = "▶ Play Original";
              status.innerText = "✅ Song finished";
          };
      } else {
          // Stop playing
          if (originalSource) {
              originalSource.stop();
              originalSource.disconnect();
              originalSource = null;
          }
          isSongPlaying = false;
          playBtn.innerText = "▶ Play Original";
          status.innerText = "⏹ Stopped";
      }
  };

  /* ================== HIGH QUALITY CANVAS DRAW ================== */
  function drawCanvas() {
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const canvasW = canvas.width;
      const canvasH = canvas.height * 0.75;

      const imgRatio = mainBg.naturalWidth / mainBg.naturalHeight;
      const canvasRatio = canvasW / canvasH;

      let drawW, drawH;
      if (imgRatio > canvasRatio) {
          drawW = canvasW;
          drawH = canvasW / imgRatio;
      } else {
          drawH = canvasH;
          drawW = canvasH * imgRatio;
      }

      const x = (canvasW - drawW) / 2;
      const y = 0;

      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(mainBg, x, y, drawW, drawH);
      
      const logoSize = 60;
      ctx.drawImage(logoImg, 20, 20, logoSize, logoSize);

      canvasRafId = requestAnimationFrame(drawCanvas);
  }

  /* ================== FIXED: VOICE + ACCOMPANIMENT RECORDING ================== */
  recordBtn.onclick = async function() {
      if (isRecording) return;
      
      isRecording = true;
      playBtn.style.display = "none";
      recordBtn.style.display = "none";
      stopBtn.style.display = "inline-block";
      status.innerText = "🎙 Starting recording...";
      
      try {
          const audioCtx = await ensureAudioContext();
          
          // Clear previous timer
          if (autoStopTimer) {
              clearTimeout(autoStopTimer);
              autoStopTimer = null;
          }
          
          // Stop any currently playing song
          if (isSongPlaying && originalSource) {
              originalSource.stop();
              originalSource.disconnect();
              originalSource = null;
              isSongPlaying = false;
          }
          
          // Load audio buffers if not loaded
          if (!originalAudioBuffer || !accompanimentBuffer) {
              await loadAudioBuffers();
          }
          
          // ✅ CRITICAL FIX: Play original song through separate audio element (not recorded)
          // Create hidden audio element for original song playback
          const playbackAudio = new Audio(originalAudio.getAttribute('data-src'));
          playbackAudio.volume = 1.0;
          playbackAudio.play().catch(e => console.log("Playback error:", e));
          
          // Get microphone with optimized settings for CLEAR VOICE
          micStream = await navigator.mediaDevices.getUserMedia({
              audio: {
                  echoCancellation: false,  // Better for voice clarity
                  noiseSuppression: true,   // Reduce background noise
                  autoGainControl: false,   // Manual control
                  channelCount: 1,
                  sampleRate: 48000,
                  sampleSize: 24,
                  latency: 0.01
              },
              video: false
          }).catch(err => {
              status.innerText = "❌ Microphone access required";
              resetUIOnError();
              throw err;
          });
          
          // Create microphone source
          micSource = audioCtx.createMediaStreamSource(micStream);
          
          // Create accompaniment source from buffer
          accSource = audioCtx.createBufferSource();
          accSource.buffer = accompanimentBuffer;
          
          // Get ACTUAL duration
          const actualDuration = accompanimentBuffer.duration;
          console.log("✅ Actual accompaniment duration:", actualDuration, "seconds");
          
          // Create gain nodes with optimal settings for CLEAR RECORDING
          micGain = audioCtx.createGain();
          micGain.gain.value = 1.5;  // Voice volume - CLEAR
          
          accGain = audioCtx.createGain();
          accGain.gain.value = 0.4;  // Accompaniment volume
          
          // Create destination for recording
          destination = audioCtx.createMediaStreamDestination();
          
          // ✅ IMPORTANT: Connect ONLY microphone and accompaniment to recording
          // Original song is played separately and NOT connected to recording
          micSource.connect(micGain);
          micGain.connect(destination);
          accSource.connect(accGain);
          accGain.connect(destination);
          
          # Start canvas drawing
          drawCanvas();
          
          # Start accompaniment for recording
          accSource.start();
          
          # Create stream from canvas
          const canvasStream = canvas.captureStream(30);
          const mixedAudioStream = destination.stream;
          
          # Combine video and audio streams
          const combinedStream = new MediaStream([
              ...canvasStream.getVideoTracks(),
              ...mixedAudioStream.getAudioTracks()
          ]);
          
          # ✅ FIXED: USE MP4 FORMAT FOR BETTER COMPATIBILITY
          let mimeType = 'video/mp4;codecs=avc1.42E01E,mp4a.40.2';
          if (!MediaRecorder.isTypeSupported(mimeType)) {
              mimeType = 'video/webm;codecs=vp9,opus';
          }
          if (!MediaRecorder.isTypeSupported(mimeType)) {
              mimeType = 'video/webm;codecs=vp8,opus';
          }
          if (!MediaRecorder.isTypeSupported(mimeType)) {
              mimeType = 'video/webm';
          }
          
          # Create MediaRecorder with optimal settings
          mediaRecorder = new MediaRecorder(combinedStream, {
              mimeType: mimeType,
              audioBitsPerSecond: 256000,    # High quality audio
              videoBitsPerSecond: 5000000,   # High quality video
              videoKeyFrameInterval: 30
          });
          
          recordedChunks = [];
          recordingStartTime = Date.now();
          
          mediaRecorder.ondataavailable = e => {
              if (e.data.size > 0) {
                  recordedChunks.push(e.data);
              }
          };
          
          mediaRecorder.onstop = () => {
              cancelAnimationFrame(canvasRafId);
              recordingDuration = (Date.now() - recordingStartTime) / 1000;
              
              # Stop playback audio
              playbackAudio.pause();
              playbackAudio.currentTime = 0;
              
              # Cleanup audio sources
              cleanupAudioSources();
              
              # Create blob
              if (recordedChunks.length > 0) {
                  const blob = new Blob(recordedChunks, { type: mimeType });
                  const url = URL.createObjectURL(blob);
                  
                  if (lastRecordingURL) URL.revokeObjectURL(lastRecordingURL);
                  lastRecordingURL = url;
                  
                  finalBg.src = mainBg.src;
                  finalDiv.style.display = "flex";
                  
                  # Show actual recording duration
                  const minutes = Math.floor(recordingDuration / 60);
                  const seconds = Math.floor(recordingDuration % 60);
                  finalStatus.innerText = `✅ Recording Complete! (${minutes}:${seconds.toString().padStart(2, '0')})`;
                  
                  # ✅ FIXED: Set download link with proper metadata
                  const songName = "%%SONG_NAME%%".replace(/[^a-zA-Z0-9]/g, '_');
                  
                  # Determine file extension
                  let extension = '';
                  if (mimeType.includes('mp4')) {
                      extension = '_KARAOKE.mp4';
                  } else {
                      extension = '_KARAOKE.webm';
                  }
                  
                  const fileName = songName + extension;
                  downloadRecordingBtn.href = url;
                  downloadRecordingBtn.download = fileName;
                  
                  # ✅ FIXED: Play recording in same interface
                  playRecordingBtn.onclick = () => {
                      if (!isPlayingRecording) {
                          # Show video player
                          recordingVideoPlayer.src = url;
                          recordingVideoPlayer.style.display = 'block';
                          videoControls.style.display = 'flex';
                          
                          # Hide final output
                          finalDiv.style.display = 'none';
                          
                          # Play the video
                          recordingVideoPlayer.play();
                          
                          playRecordingBtn.innerText = "⏹ Stop";
                          isPlayingRecording = true;
                          
                          # Update button text when video ends
                          recordingVideoPlayer.onended = () => {
                              closeVideoPlayer();
                              playRecordingBtn.innerText = "▶ Play";
                              isPlayingRecording = false;
                          };
                      } else {
                          closeVideoPlayer();
                          playRecordingBtn.innerText = "▶ Play";
                          isPlayingRecording = false;
                      }
                  };
              }
          };
          
          # Start recording
          mediaRecorder.start(1000);
          
          status.innerText = "🎙 Recording... Original song playing (not recorded) + Your voice + Accompaniment";
          
          # AUTO-STOP TIMER based on accompaniment duration
          autoStopTimer = setTimeout(() => {
              if (isRecording) {
                  stopRecording();
                  status.innerText = "✅ Auto-stopped: Recording complete!";
              }
          }, (actualDuration * 1000) + 1000);
          
      } catch (error) {
          console.error("Recording error:", error);
          status.innerText = "❌ Failed: " + (error.message || "Check microphone access");
          resetUIOnError();
      }
  };

  /* ================== CLEANUP AUDIO SOURCES ================== */
  function cleanupAudioSources() {
      if (accSource) {
          try { 
              accSource.stop(); 
              accSource.disconnect();
          } catch(e) {}
          accSource = null;
      }
      
      if (originalSource) {
          try { 
              originalSource.stop(); 
              originalSource.disconnect();
          } catch(e) {}
          originalSource = null;
      }
      
      if (micSource) {
          try { 
              micSource.disconnect(); 
          } catch(e) {}
          micSource = null;
      }
      
      if (micGain) {
          try {
              micGain.disconnect();
          } catch(e) {}
          micGain = null;
      }
      
      if (accGain) {
          try {
              accGain.disconnect();
          } catch(e) {}
          accGain = null;
      }
      
      if (destination) {
          try {
              destination.disconnect();
          } catch(e) {}
          destination = null;
      }
      
      if (micStream) {
          micStream.getTracks().forEach(track => track.stop());
          micStream = null;
      }
  }

  /* ================== STOP RECORDING ================== */
  function stopRecording() {
      if (!isRecording) return;
      
      # Clear timer
      if (autoStopTimer) {
          clearTimeout(autoStopTimer);
          autoStopTimer = null;
      }
      
      # Stop media recorder
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
          mediaRecorder.stop();
      }
      
      # Cleanup audio sources
      cleanupAudioSources();
      
      # Stop original song if playing
      if (isSongPlaying && originalSource) {
          originalSource.stop();
          originalSource.disconnect();
          originalSource = null;
          isSongPlaying = false;
      }
      
      # Stop canvas
      if (canvasRafId) {
          cancelAnimationFrame(canvasRafId);
          canvasRafId = null;
      }
      
      # Update UI
      isRecording = false;
      stopBtn.style.display = "none";
      status.innerText = "Processing recording...";
  }

  /* ================== STOP BUTTON CLICK ================== */
  stopBtn.onclick = function() {
      stopRecording();
  };

  /* ================== NEW RECORDING ================== */
  newRecordingBtn.onclick = function() {
      closeVideoPlayer();
      finalDiv.style.display = "none";
      
      # Reset audio
      if (isSongPlaying && originalSource) {
          originalSource.stop();
          originalSource.disconnect();
          originalSource = null;
          isSongPlaying = false;
      }
      
      # Reset UI
      playBtn.style.display = "inline-block";
      playBtn.innerText = "▶ Play Original";
      recordBtn.style.display = "inline-block";
      stopBtn.style.display = "none";
      status.innerText = "Ready 🎤";
      
      # Reset state
      recordedChunks = [];
      isRecording = false;
      isPlayingRecording = false;
      recordingStartTime = 0;
      recordingDuration = 0;
      
      # Release URL
      if (lastRecordingURL) {
          URL.revokeObjectURL(lastRecordingURL);
          lastRecordingURL = null;
      }
  };

  /* ================== VIDEO PLAYER FUNCTIONS ================== */
  function closeVideoPlayer() {
      if (recordingVideoPlayer) {
          recordingVideoPlayer.pause();
          recordingVideoPlayer.currentTime = 0;
          recordingVideoPlayer.style.display = 'none';
          videoControls.style.display = 'none';
          recordingVideoPlayer.src = '';
      }
      finalDiv.style.display = 'flex';
      playRecordingBtn.innerText = "▶ Play";
      isPlayingRecording = false;
      
      # Exit fullscreen if active
      if (document.fullscreenElement) {
          document.exitFullscreen();
      }
  }

  function toggleFullscreen() {
      if (!document.fullscreenElement) {
          recordingVideoPlayer.requestFullscreen().catch(err => {
              console.log("Fullscreen error:", err);
          });
      } else {
          document.exitFullscreen();
      }
  }

  /* ================== HELPER FUNCTIONS ================== */
  function resetUIOnError() {
      isRecording = false;
      playBtn.style.display = "inline-block";
      playBtn.innerText = "▶ Play Original";
      recordBtn.style.display = "inline-block";
      stopBtn.style.display = "none";
      
      # Reset song playing state
      isSongPlaying = false;
      
      # Stop original song
      if (originalSource) {
          originalSource.stop();
          originalSource.disconnect();
          originalSource = null;
      }
      
      if (autoStopTimer) {
          clearTimeout(autoStopTimer);
          autoStopTimer = null;
      }
      
      # Cleanup
      cleanupAudioSources();
  }

  /* ================== TOUCH EVENTS FOR MOBILE ================== */
  document.addEventListener('touchstart', async () => {
      await ensureAudioContext();
  }, { once: true });

  /* ================== INITIALIZE ================== */
  window.addEventListener('load', async () => {
      status.innerText = "Ready 🎤 - Tap screen first";
      
      # Pre-warm audio context and load buffers
      try {
          await ensureAudioContext();
          await loadAudioBuffers();
          status.innerText = "Ready 🎤 - Click 'Play Original' to listen";
      } catch(e) {
          console.log("Initialization error:", e);
          status.innerText = "Ready 🎤";
      }
  });

  /* ================== CLEANUP ================== */
  window.addEventListener('beforeunload', () => {
      if (lastRecordingURL) {
          URL.revokeObjectURL(lastRecordingURL);
      }
      if (audioContext) {
          audioContext.close();
      }
      cleanupAudioSources();
  });

  /* ================== VIDEO PLAYER EVENT LISTENERS ================== */
  recordingVideoPlayer.addEventListener('click', function() {
      if (this.paused) {
          this.play();
      } else {
          this.pause();
      }
  });

  document.addEventListener('fullscreenchange', function() {
      if (!document.fullscreenElement) {
          videoControls.style.display = 'flex';
      }
  });
  </script>
</body>
</html>
"""

    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")
    karaoke_html = karaoke_html.replace("%%SONG_NAME%%", selected_song)
    karaoke_html = karaoke_html.replace("%%SONG_DURATION%%", str(song_duration))

    # Back button
    if st.session_state.role in ["admin", "user"]:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("← Back", key="back_player", type="secondary"):
                st.session_state.page = "User Dashboard"
                st.session_state.selected_song = None
                
                if "song" in st.query_params:
                    del st.query_params["song"]
                
                save_session_to_db()
                st.rerun()

    # Display karaoke player
    html(f'<div class="karaoke-container">{karaoke_html}</div>', height=640, width=360, scrolling=False)

# =============== FALLBACK ===============
else:
    if "song" in st.query_params:
        st.session_state.page = "Song Player"
    else:
        st.session_state.page = "User Dashboard"
    save_session_to_db()
    st.rerun()
