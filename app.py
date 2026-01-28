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

# Set page config with mobile optimization
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

# =============== ACCURATE AUDIO DURATION FUNCTIONS ===============
def get_audio_duration_ffprobe(file_path):
    """Get accurate audio duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error', 
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            return max(duration, 1.0)  # Ensure at least 1 second
    except:
        pass
    return None

def get_audio_duration_pydub(file_path):
    """Fallback using pydub"""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0  # Convert to seconds
    except:
        pass
    return None

def get_audio_duration_wave(file_path):
    """Fallback for WAV files"""
    try:
        import wave
        with wave.open(file_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            return frames / float(rate)
    except:
        pass
    return None

def get_audio_duration(file_path):
    """Get accurate audio duration using multiple methods"""
    if not os.path.exists(file_path):
        return 180.0  # Default 3 minutes
    
    # Try ffprobe first
    duration = get_audio_duration_ffprobe(file_path)
    if duration:
        return duration
    
    # Try pydub
    duration = get_audio_duration_pydub(file_path)
    if duration:
        return duration
    
    # Try wave
    duration = get_audio_duration_wave(file_path)
    if duration:
        return duration
    
    # Last resort: estimate from file size (for MP3)
    try:
        file_size = os.path.getsize(file_path)
        # Rough estimate: 1MB ≈ 1 minute at 128kbps
        estimated = (file_size / (128 * 125)) * 60
        return max(estimated, 30.0)  # Minimum 30 seconds
    except:
        return 180.0  # Default 3 minutes

def fix_audio_duration(input_path, output_path):
    """Fix audio duration metadata using ffmpeg"""
    try:
        cmd = [
            'ffmpeg', '-i', input_path,
            '-c:a', 'copy',  # Copy audio codec
            '-map_metadata', '0',
            '-movflags', '+faststart',
            '-y',  # Overwrite
            output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=10)
        return True
    except:
        try:
            import shutil
            shutil.copy2(input_path, output_path)
            return True
        except:
            return False

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
                      duration REAL,
                      file_size INTEGER,
                      bitrate INTEGER)''')
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

def save_metadata_to_db(song_name, uploaded_by, duration=None, file_size=None, bitrate=None):
    """Save metadata to database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO metadata 
                     (song_name, uploaded_by, timestamp, duration, file_size, bitrate)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (song_name, uploaded_by, time.time(), duration, file_size, bitrate))
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
        c.execute('SELECT song_name, uploaded_by, duration, file_size, bitrate FROM metadata')
        results = c.fetchall()
        conn.close()
        
        for song_name, uploaded_by, duration, file_size, bitrate in results:
            metadata[song_name] = {
                "uploaded_by": uploaded_by, 
                "timestamp": str(time.time()),
                "duration": duration,
                "file_size": file_size,
                "bitrate": bitrate
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
        file_size = info.get("file_size")
        bitrate = info.get("bitrate")
        save_metadata_to_db(song_name, uploaded_by, duration, file_size, bitrate)

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
        
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
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
    """Get accurate duration for a song"""
    metadata = get_metadata_cached()
    
    if song_name in metadata and "duration" in metadata[song_name]:
        duration = metadata[song_name]["duration"]
        if duration and duration > 0:
            return duration
    
    # Calculate duration from accompaniment file
    acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
    if os.path.exists(acc_path):
        try:
            # Get accurate duration
            duration = get_audio_duration(acc_path)
            
            # Get file info
            file_size = os.path.getsize(acc_path)
            bitrate = int((file_size * 8) / duration) if duration > 0 else 128000
            
            # Store in metadata
            if song_name in metadata:
                metadata[song_name]["duration"] = duration
                metadata[song_name]["file_size"] = file_size
                metadata[song_name]["bitrate"] = bitrate
            else:
                metadata[song_name] = {
                    "uploaded_by": "unknown",
                    "duration": duration,
                    "file_size": file_size,
                    "bitrate": bitrate
                }
            
            save_metadata(metadata)
            get_metadata_cached.clear()
            return duration
        except Exception as e:
            print(f"Error calculating duration for {song_name}: {e}")
    
    return 180.0  # Default 3 minutes if cannot determine

# =============== MOBILE DETECTION ===============
def is_mobile():
    """Detect if running on mobile device"""
    user_agent = st.query_params.get("user_agent", "")
    if user_agent:
        mobile_indicators = ['Mobile', 'Android', 'iPhone', 'iPad', 'iPod']
        return any(indicator in user_agent for indicator in mobile_indicators)
    return False

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
if "mobile_mode" not in st.session_state:
    st.session_state.mobile_mode = is_mobile()

# Load persistent session data
load_session_from_db()

# Process query parameters FIRST
process_query_params()

# Get cached metadata
metadata = get_metadata_cached()

# Logo
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
if not os.path.exists(default_logo_path):
    # Create default logo if not exists
    try:
        img = Image.new('RGB', (512, 512), color='#1E3A8A')
        d = ImageDraw.Draw(img)
        d.text((200, 220), "🎤", fill='white', font_size=100)
        img.save(default_logo_path, 'PNG')
    except:
        pass

logo_b64 = file_to_base64(default_logo_path) if os.path.exists(default_logo_path) else ""

# =============== RESPONSIVE CSS FOR ALL PAGES ===============
st.markdown("""
<style>
/* Mobile Responsive Design */
@media (max-width: 768px) {
    .main .block-container {
        padding: 1rem !important;
        max-width: 100% !important;
    }
    
    h1 {
        font-size: 1.5rem !important;
    }
    
    h2 {
        font-size: 1.3rem !important;
    }
    
    h3 {
        font-size: 1.2rem !important;
    }
    
    .stButton > button {
        font-size: 14px !important;
        padding: 10px 12px !important;
        width: 100% !important;
    }
    
    .stTextInput > div > div > input {
        font-size: 16px !important; /* Prevents zoom on iOS */
        padding: 12px !important;
    }
    
    .stRadio > div[role="radiogroup"] > label {
        font-size: 14px !important;
    }
    
    .stColumn {
        padding: 5px !important;
        margin-bottom: 10px !important;
    }
    
    .song-item {
        padding: 10px !important;
        margin: 5px 0 !important;
        font-size: 14px !important;
    }
}

/* Fix for 9:16 aspect ratio on mobile */
@media (max-width: 480px) and (orientation: portrait) {
    .main .block-container {
        padding: 0.5rem !important;
        height: 100vh !important;
        aspect-ratio: 9/16 !important;
    }
    
    .stApp {
        min-height: 100vh !important;
        max-height: 100vh !important;
        overflow-y: auto !important;
    }
    
    .stButton > button {
        height: 44px !important;
        margin: 5px 0 !important;
    }
    
    /* Ensure forms fit mobile screens */
    .element-container {
        margin-bottom: 10px !important;
    }
}

/* Tablet landscape */
@media (min-width: 769px) and (max-width: 1024px) {
    .main .block-container {
        padding: 1.5rem !important;
    }
}

/* Desktop */
@media (min-width: 1025px) {
    .main .block-container {
        padding: 2rem !important;
        max-width: 1200px !important;
    }
}

/* Common mobile fixes */
button:focus {
    outline: none !important;
}

input, textarea, select {
    font-size: 16px !important; /* Prevents zoom on iOS */
}

/* Scrollbar styling for mobile */
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
</style>
""", unsafe_allow_html=True)

# =============== RESPONSIVE LOGIN PAGE ===============
if st.session_state.page == "Login":
    save_session_to_db()
    
    # Additional mobile-specific CSS for login
    st.markdown("""
    <style>
    .login-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 80vh;
        padding: 20px;
    }
    
    @media (max-width: 768px) {
        .login-container {
            min-height: 90vh;
            padding: 15px;
        }
        
        .stTextInput > div > div > input {
            height: 50px !important;
        }
        
        .stButton > button {
            height: 50px !important;
            font-size: 16px !important;
        }
    }
    
    @media (max-width: 480px) {
        .login-container {
            min-height: 100vh;
            padding: 10px;
        }
        
        .stTextInput > div > div > input {
            height: 45px !important;
        }
        
        .stButton > button {
            height: 45px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Mobile-responsive layout
    if st.session_state.mobile_mode:
        col1, col2, col3 = st.columns([0.2, 3, 0.2])
    else:
        col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Logo
        if logo_b64:
            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{logo_b64}" style="width: 80px; height: 80px; border-radius: 50%;">
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<h1 style='text-align: center; margin-bottom: 10px;'>🎤 Sing Along</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666; margin-bottom: 30px;'>Login to continue</p>", unsafe_allow_html=True)
        
        # Login form
        username = st.text_input("Username", placeholder="Enter username", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Enter password", key="login_password")
        
        login_button = st.button("Login", key="login_button", use_container_width=True)
        
        if login_button:
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
        
        # Contact info
        st.markdown("""
        <div style="margin-top: 30px; text-align: center;">
            <p style="color: #666; font-size: 14px;">Don't have access? Contact admin:</p>
            <div style="display: flex; justify-content: center; gap: 15px; margin-top: 10px; flex-wrap: wrap;">
                <a href="mailto:branks3.singalong@gmail.com" style="text-decoration: none; color: #4285F4;">
                    📧 Email
                </a>
                <a href="https://www.instagram.com/branks3.sing_along/" target="_blank" style="text-decoration: none; color: #E1306C;">
                    📸 Instagram
                </a>
                <a href="https://www.youtube.com/@branks3.sing_along" target="_blank" style="text-decoration: none; color: #FF0000;">
                    ▶ YouTube
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    save_session_to_db()
    
    # Admin dashboard CSS
    st.markdown("""
    <style>
    .admin-dashboard {
        padding: 20px;
    }
    
    .song-list-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px;
        margin: 8px 0;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .song-actions {
        display: flex;
        gap: 10px;
    }
    
    @media (max-width: 768px) {
        .admin-dashboard {
            padding: 10px;
        }
        
        .song-list-item {
            flex-direction: column;
            align-items: stretch;
            gap: 10px;
        }
        
        .song-actions {
            justify-content: space-between;
        }
        
        .song-actions button {
            flex: 1;
            margin: 0 5px;
        }
    }
    
    @media (max-width: 480px) {
        .song-list-item {
            padding: 10px;
        }
        
        .song-actions {
            flex-direction: column;
            gap: 5px;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("### Navigation")
        page_option = st.radio(
            "Go to:",
            ["Upload Songs", "Songs List", "Share Links"],
            key="admin_nav"
        )
        
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
    
    # UPLOAD SONGS PAGE
    if page_option == "Upload Songs":
        st.subheader("📤 Upload New Song")
        
        song_name = st.text_input(
            "Song Name",
            placeholder="Enter song name (e.g., MyFavoriteSong)",
            key="upload_song_name"
        )
        
        # Responsive file uploaders
        if st.session_state.mobile_mode:
            col1, col2, col3 = st.columns(1), st.columns(1), st.columns(1)
            with st.container():
                original_audio = st.file_uploader(
                    "Original Song MP3",
                    type=["mp3"],
                    key="original_upload_mobile"
                )
            with st.container():
                accompaniment = st.file_uploader(
                    "Accompaniment MP3",
                    type=["mp3"],
                    key="accompaniment_upload_mobile"
                )
            with st.container():
                lyrics_image = st.file_uploader(
                    "Lyrics Image",
                    type=["jpg", "jpeg", "png", "webp"],
                    key="lyrics_upload_mobile"
                )
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                original_audio = st.file_uploader(
                    "Original Song MP3",
                    type=["mp3"],
                    key="original_upload"
                )
            with col2:
                accompaniment = st.file_uploader(
                    "Accompaniment MP3",
                    type=["mp3"],
                    key="accompaniment_upload"
                )
            with col3:
                lyrics_image = st.file_uploader(
                    "Lyrics Image",
                    type=["jpg", "jpeg", "png", "webp"],
                    key="lyrics_upload"
                )
        
        if st.button("Upload Song", type="primary", use_container_width=True):
            if not song_name:
                st.error("❌ Please enter a song name")
            elif not original_audio or not accompaniment:
                st.error("❌ Please upload both audio files")
            elif not lyrics_image:
                st.error("❌ Please upload lyrics image")
            else:
                # Clean song name
                song_name_clean = song_name.strip().replace(" ", "_")
                
                # Save files
                original_path = os.path.join(songs_dir, f"{song_name_clean}_original.mp3")
                acc_path = os.path.join(songs_dir, f"{song_name_clean}_accompaniment.mp3")
                lyrics_ext = os.path.splitext(lyrics_image.name)[1].lower()
                lyrics_path = os.path.join(lyrics_dir, f"{song_name_clean}_lyrics_bg{lyrics_ext}")
                
                try:
                    # Save files
                    with open(original_path, "wb") as f:
                        f.write(original_audio.getbuffer())
                    with open(acc_path, "wb") as f:
                        f.write(accompaniment.getbuffer())
                    with open(lyrics_path, "wb") as f:
                        f.write(lyrics_image.getbuffer())
                    
                    # Fix audio durations
                    fix_audio_duration(original_path, original_path)
                    fix_audio_duration(acc_path, acc_path)
                    
                    # Calculate and store duration
                    duration = get_audio_duration(acc_path)
                    file_size = os.path.getsize(acc_path)
                    bitrate = int((file_size * 8) / duration) if duration > 0 else 128000
                    
                    # Update metadata
                    metadata = get_metadata_cached()
                    metadata[song_name_clean] = {
                        "uploaded_by": st.session_state.user,
                        "timestamp": time.time(),
                        "duration": duration,
                        "file_size": file_size,
                        "bitrate": bitrate
                    }
                    save_metadata(metadata)
                    
                    # Clear caches
                    get_song_files_cached.clear()
                    get_metadata_cached.clear()
                    
                    st.success(f"✅ Song '{song_name_clean}' uploaded successfully!")
                    st.info(f"⏱️ Duration: {int(duration//60)}:{int(duration%60):02d}")
                    st.balloons()
                    
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")
    
    # SONGS LIST PAGE
    elif page_option == "Songs List":
        st.subheader("🎵 All Songs")
        
        # Search
        search_query = st.text_input(
            "Search songs",
            placeholder="Type to search...",
            key="admin_search"
        )
        st.session_state.search_query = search_query
        
        # Get songs
        all_songs = get_song_files_cached()
        
        if search_query:
            all_songs = [s for s in all_songs if search_query.lower() in s.lower()]
        
        if not all_songs:
            st.warning("No songs found")
        else:
            for song in all_songs:
                # Get song info
                duration = get_song_duration(song)
                duration_str = f"{int(duration//60)}:{int(duration%60):02d}"
                
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    if st.button(
                        f"🎵 {song} ({duration_str})",
                        key=f"play_{song}",
                        use_container_width=True,
                        help="Click to play"
                    ):
                        open_song_player(song)
                
                with col2:
                    if st.button("🔗", key=f"share_{song}", help="Share link"):
                        safe_song = quote(song)
                        share_url = f"{APP_URL}?song={safe_song}"
                        st.success(f"Share URL: {share_url}")
                
                with col3:
                    if st.button("🗑️", key=f"delete_{song}", type="secondary", help="Delete song"):
                        st.session_state.confirm_delete = song
            
            # Delete confirmation
            if st.session_state.confirm_delete:
                song_to_delete = st.session_state.confirm_delete
                st.warning(f"Are you sure you want to delete '{song_to_delete}'?")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Delete", type="primary", use_container_width=True):
                        if delete_song_files(song_to_delete):
                            delete_metadata(song_to_delete)
                            delete_shared_link(song_to_delete)
                            st.success(f"✅ Song deleted!")
                            st.session_state.confirm_delete = None
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete song")
                
                with col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.confirm_delete = None
                        st.rerun()
    
    # SHARE LINKS PAGE
    elif page_option == "Share Links":
        st.subheader("🔗 Manage Shared Links")
        
        all_songs = get_song_files_cached()
        shared_links = get_shared_links_cached()
        
        for song in all_songs:
            is_shared = song in shared_links
            status = "✅ Shared" if is_shared else "❌ Not Shared"
            
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{song}** - {status}")
            
            with col2:
                if is_shared:
                    if st.button("🚫", key=f"unshare_{song}", help="Unshare"):
                        delete_shared_link(song)
                        get_shared_links_cached.clear()
                        st.success(f"✅ Unshared '{song}'")
                        time.sleep(0.5)
                        st.rerun()
                else:
                    if st.button("🔗", key=f"share_{song}", help="Share"):
                        save_shared_link(song, {"shared_by": st.session_state.user, "active": True})
                        get_shared_links_cached.clear()
                        st.success(f"✅ Shared '{song}'")
                        time.sleep(0.5)
                        st.rerun()
            
            with col3:
                if is_shared:
                    safe_song = quote(song)
                    share_url = f"{APP_URL}?song={safe_song}"
                    st.markdown(f'<a href="{share_url}" target="_blank">🔗 Link</a>', unsafe_allow_html=True)

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    save_session_to_db()
    
    # User dashboard CSS
    st.markdown("""
    <style>
    .user-dashboard {
        padding: 20px;
    }
    
    .user-song-item {
        padding: 15px;
        margin: 10px 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
        cursor: pointer;
        transition: transform 0.2s;
    }
    
    .user-song-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    
    @media (max-width: 768px) {
        .user-dashboard {
            padding: 10px;
        }
        
        .user-song-item {
            padding: 12px;
            margin: 8px 0;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"🎵 Welcome, {st.session_state.user}!")
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Quick Actions")
        if st.button("🔄 Refresh", use_container_width=True):
            get_song_files_cached.clear()
            get_shared_links_cached.clear()
            st.rerun()
        
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
    
    # Main content
    st.subheader("Available Songs")
    
    # Search
    search_query = st.text_input(
        "Search songs",
        placeholder="Type to search...",
        key="user_search"
    )
    
    # Get songs
    all_songs = get_song_files_cached()
    shared_links = get_shared_links_cached()
    available_songs = [s for s in all_songs if s in shared_links]
    
    if search_query:
        available_songs = [s for s in available_songs if search_query.lower() in s.lower()]
    
    if not available_songs:
        st.info("No songs available. Ask admin to share songs.")
    else:
        # Mobile layout
        if st.session_state.mobile_mode:
            cols_per_row = 1
        else:
            cols_per_row = 3
        
        cols = st.columns(cols_per_row)
        for idx, song in enumerate(available_songs):
            col_idx = idx % cols_per_row
            with cols[col_idx]:
                duration = get_song_duration(song)
                duration_str = f"{int(duration//60)}:{int(duration%60):02d}"
                
                if st.button(
                    f"🎤 {song}\n⏱️ {duration_str}",
                    key=f"user_play_{song}",
                    use_container_width=True,
                    type="primary"
                ):
                    open_song_player(song)

# =============== SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    save_session_to_db()
    
    selected_song = st.session_state.selected_song
    
    # Check access
    shared_links = get_shared_links_cached()
    is_admin = st.session_state.role == "admin"
    is_user = st.session_state.role == "user"
    is_shared = selected_song in shared_links
    
    if not (is_admin or (is_user and is_shared)):
        st.error("❌ Access denied! This song is not shared.")
        if st.button("Go Back"):
            if is_admin:
                st.session_state.page = "Admin Dashboard"
            elif is_user:
                st.session_state.page = "User Dashboard"
            save_session_to_db()
            st.rerun()
        st.stop()
    
    # Get file paths
    original_path = os.path.join(songs_dir, f"{selected_song}_original.mp3")
    accompaniment_path = os.path.join(songs_dir, f"{selected_song}_accompaniment.mp3")
    
    # Find lyrics image
    lyrics_path = ""
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        p = os.path.join(lyrics_dir, f"{selected_song}_lyrics_bg{ext}")
        if os.path.exists(p):
            lyrics_path = p
            break
    
    # Check if files exist
    if not os.path.exists(accompaniment_path):
        st.error(f"❌ Song '{selected_song}' not found!")
        if st.button("Go Back"):
            if is_admin:
                st.session_state.page = "Admin Dashboard"
            elif is_user:
                st.session_state.page = "User Dashboard"
            save_session_to_db()
            st.rerun()
        st.stop()
    
    # Get accurate duration
    song_duration = get_song_duration(selected_song)
    
    # Convert files to base64
    original_b64 = file_to_base64(original_path) if os.path.exists(original_path) else ""
    accompaniment_b64 = file_to_base64(accompaniment_path)
    lyrics_b64 = file_to_base64(lyrics_path)
    
    # Back button
    if st.session_state.role in ["admin", "user"]:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("← Back", type="secondary", use_container_width=True):
                if st.session_state.role == "admin":
                    st.session_state.page = "Admin Dashboard"
                else:
                    st.session_state.page = "User Dashboard"
                st.session_state.selected_song = None
                if "song" in st.query_params:
                    del st.query_params["song"]
                save_session_to_db()
                st.rerun()
    
    # =============== ENHANCED KARAOKE PLAYER ===============
    # Mobile-optimized karaoke player with voice clarity fix
    karaoke_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🎤 {selected_song} - Sing Along</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }}
        
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #000;
            font-family: 'Arial', sans-serif;
        }}
        
        body {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
        }}
        
        #container {{
            width: 100%;
            height: 100%;
            max-width: 480px; /* Mobile width */
            max-height: 853px; /* 9:16 aspect ratio */
            position: relative;
            background: #000;
            overflow: hidden;
        }}
        
        #backgroundImage {{
            width: 100%;
            height: 70%;
            object-fit: contain;
            background: #111;
        }}
        
        #logo {{
            position: absolute;
            top: 15px;
            left: 15px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            z-index: 10;
        }}
        
        #status {{
            position: absolute;
            top: 20px;
            width: 100%;
            text-align: center;
            color: white;
            font-size: 14px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
            z-index: 10;
            padding: 0 20px;
        }}
        
        #controls {{
            position: absolute;
            bottom: 20px;
            width: 100%;
            padding: 0 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            z-index: 10;
        }}
        
        .control-row {{
            display: flex;
            gap: 10px;
            justify-content: center;
        }}
        
        button {{
            flex: 1;
            padding: 14px 20px;
            border: none;
            border-radius: 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            min-height: 50px;
            max-width: 200px;
        }}
        
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
        }}
        
        button:active {{
            transform: translateY(0);
        }}
        
        #recordBtn {{
            background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        }}
        
        #stopBtn {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        
        #playOriginalBtn {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        
        #playbackSection {{
            display: none;
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 100;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        #playbackControls {{
            display: flex;
            gap: 15px;
            margin-top: 20px;
            flex-wrap: wrap;
            justify-content: center;
        }}
        
        #playbackTitle {{
            color: white;
            font-size: 20px;
            margin-bottom: 20px;
            text-align: center;
        }}
        
        /* Progress bar */
        #progressContainer {{
            width: 90%;
            height: 6px;
            background: rgba(255,255,255,0.2);
            border-radius: 3px;
            margin: 15px auto;
            position: relative;
        }}
        
        #progressBar {{
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 3px;
            transition: width 0.1s;
        }}
        
        /* Timer */
        #timer {{
            color: white;
            font-size: 12px;
            text-align: center;
            margin-top: 5px;
        }}
        
        /* Mobile optimizations */
        @media (max-width: 480px) {{
            button {{
                padding: 12px 16px;
                font-size: 13px;
                min-height: 45px;
            }}
            
            #controls {{
                padding: 0 15px;
                bottom: 15px;
            }}
            
            #status {{
                font-size: 13px;
                top: 15px;
            }}
        }}
        
        @media (max-width: 320px) {{
            button {{
                padding: 10px 14px;
                font-size: 12px;
                min-height: 40px;
            }}
            
            #controls {{
                padding: 0 10px;
                bottom: 10px;
            }}
        }}
        
        /* Recording indicator */
        .recording-indicator {{
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #ff0000;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
            margin-right: 8px;
        }}
        
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
            100% {{ opacity: 1; }}
        }}
    </style>
</head>
<body>
    <div id="container">
        <img id="backgroundImage" src="data:image/jpeg;base64,{lyrics_b64}" onerror="this.style.display='none'">
        <img id="logo" src="data:image/png;base64,{logo_b64}" onerror="this.style.display='none'">
        
        <div id="status">Ready to sing! 🎤</div>
        
        <div id="progressContainer">
            <div id="progressBar"></div>
        </div>
        <div id="timer">0:00 / 0:00</div>
        
        <div id="controls">
            <div class="control-row">
                <button id="playOriginalBtn">▶ Play Original</button>
                <button id="recordBtn">🎙 Start Recording</button>
            </div>
            <div class="control-row">
                <button id="stopBtn" style="display:none;">⏹ Stop Recording</button>
            </div>
        </div>
        
        <div id="playbackSection">
            <div id="playbackTitle">🎵 Recording Complete!</div>
            <div id="playbackControls">
                <button id="playRecordingBtn">▶ Play Recording</button>
                <button id="downloadBtn">⬇ Download</button>
                <button id="newRecordingBtn">🔄 New Recording</button>
            </div>
        </div>
    </div>
    
    <!-- Audio elements -->
    <audio id="originalAudio" src="data:audio/mp3;base64,{original_b64}" preload="auto"></audio>
    <audio id="accompanimentAudio" src="data:audio/mp3;base64,{accompaniment_b64}" preload="auto"></audio>
    
    <script>
        // Global variables
        let mediaRecorder = null;
        let recordedChunks = [];
        let recordingStream = null;
        let audioContext = null;
        let mediaStreamSource = null;
        let destination = null;
        let isRecording = false;
        let recordingStartTime = 0;
        let progressInterval = null;
        let totalDuration = {song_duration}; // Song duration in seconds
        let playRecordingAudio = null;
        
        // DOM elements
        const elements = {{
            container: document.getElementById('container'),
            backgroundImage: document.getElementById('backgroundImage'),
            status: document.getElementById('status'),
            playOriginalBtn: document.getElementById('playOriginalBtn'),
            recordBtn: document.getElementById('recordBtn'),
            stopBtn: document.getElementById('stopBtn'),
            originalAudio: document.getElementById('originalAudio'),
            accompanimentAudio: document.getElementById('accompanimentAudio'),
            progressBar: document.getElementById('progressBar'),
            timer: document.getElementById('timer'),
            playbackSection: document.getElementById('playbackSection'),
            playRecordingBtn: document.getElementById('playRecordingBtn'),
            downloadBtn: document.getElementById('downloadBtn'),
            newRecordingBtn: document.getElementById('newRecordingBtn')
        }};
        
        // Initialize
        function init() {{
            console.log('Initializing karaoke player...');
            
            // Set up event listeners
            elements.playOriginalBtn.addEventListener('click', toggleOriginalPlayback);
            elements.recordBtn.addEventListener('click', startRecording);
            elements.stopBtn.addEventListener('click', stopRecording);
            elements.playRecordingBtn.addEventListener('click', playRecording);
            elements.downloadBtn.addEventListener('click', downloadRecording);
            elements.newRecordingBtn.addEventListener('click', newRecording);
            
            // Update timer
            updateTimer(0, totalDuration);
            
            // Pre-warm audio context for mobile
            if (isMobile()) {{
                setTimeout(() => {{
                    initAudioContext();
                }}, 1000);
            }}
        }}
        
        // Mobile detection
        function isMobile() {{
            return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        }}
        
        // Initialize audio context
        async function initAudioContext() {{
            if (!audioContext) {{
                audioContext = new (window.AudioContext || window.webkitAudioContext)({{
                    sampleRate: 44100,
                    latencyHint: 'interactive'
                }});
            }}
            if (audioContext.state === 'suspended') {{
                await audioContext.resume();
            }}
            return audioContext;
        }}
        
        // Update progress bar and timer
        function updateProgress(currentTime) {{
            const progress = (currentTime / totalDuration) * 100;
            elements.progressBar.style.width = progress + '%';
            
            const currentTimeFormatted = formatTime(currentTime);
            const totalTimeFormatted = formatTime(totalDuration);
            elements.timer.textContent = `${{currentTimeFormatted}} / ${{totalTimeFormatted}}`;
        }}
        
        // Format time (seconds to MM:SS)
        function formatTime(seconds) {{
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${{mins.toString().padStart(2, '0')}}:${{secs.toString().padStart(2, '0')}}`;
        }}
        
        // Update timer display
        function updateTimer(current, total) {{
            elements.timer.textContent = `${{formatTime(current)}} / ${{formatTime(total)}}`;
        }}
        
        // Toggle original audio playback
        function toggleOriginalPlayback() {{
            if (elements.originalAudio.paused) {{
                elements.originalAudio.currentTime = 0;
                elements.originalAudio.play()
                    .then(() => {{
                        elements.playOriginalBtn.textContent = '⏸ Pause Original';
                        elements.status.textContent = 'Playing original song...';
                        
                        // Update progress
                        clearInterval(progressInterval);
                        progressInterval = setInterval(() => {{
                            updateProgress(elements.originalAudio.currentTime);
                            if (elements.originalAudio.currentTime >= totalDuration) {{
                                clearInterval(progressInterval);
                                elements.playOriginalBtn.textContent = '▶ Play Original';
                                elements.status.textContent = 'Ready to sing! 🎤';
                            }}
                        }}, 100);
                    }})
                    .catch(error => {{
                        console.error('Playback error:', error);
                        elements.status.textContent = 'Error playing audio';
                    }});
            }} else {{
                elements.originalAudio.pause();
                elements.playOriginalBtn.textContent = '▶ Play Original';
                elements.status.textContent = 'Paused';
                clearInterval(progressInterval);
            }}
        }}
        
        // Start recording
        async function startRecording() {{
            if (isRecording) return;
            
            try {{
                // Initialize audio context
                await initAudioContext();
                
                // Request microphone access with optimized settings for mobile
                const constraints = {{
                    audio: {{
                        echoCancellation: {str(isMobile()).lower()},
                        noiseSuppression: false,
                        autoGainControl: true,
                        channelCount: 1,
                        sampleRate: 44100,
                        sampleSize: 16,
                        volume: 1.0
                    }},
                    video: false
                }};
                
                const stream = await navigator.mediaDevices.getUserMedia(constraints);
                recordingStream = stream;
                
                // Create media recorder
                const options = {{
                    mimeType: 'audio/webm;codecs=opus',
                    audioBitsPerSecond: 128000
                }};
                
                mediaRecorder = new MediaRecorder(stream, options);
                recordedChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {{
                    if (event.data.size > 0) {{
                        recordedChunks.push(event.data);
                    }}
                }};
                
                mediaRecorder.onstop = () => {{
                    showPlaybackSection();
                }};
                
                // Start recording
                mediaRecorder.start(100); // Collect data every 100ms
                isRecording = true;
                recordingStartTime = Date.now();
                
                // Start accompaniment
                elements.accompanimentAudio.currentTime = 0;
                elements.accompanimentAudio.play().catch(e => {{
                    console.log('Accompaniment play error:', e);
                }});
                
                // Update UI
                elements.recordBtn.style.display = 'none';
                elements.stopBtn.style.display = 'block';
                elements.status.innerHTML = '<span class="recording-indicator"></span> Recording... Sing now!';
                elements.playOriginalBtn.disabled = true;
                
                // Start progress update
                clearInterval(progressInterval);
                progressInterval = setInterval(() => {{
                    const elapsed = (Date.now() - recordingStartTime) / 1000;
                    updateProgress(elapsed);
                    
                    // Auto-stop after song duration
                    if (elapsed >= totalDuration) {{
                        stopRecording();
                    }}
                }}, 100);
                
            }} catch (error) {{
                console.error('Recording error:', error);
                elements.status.textContent = 'Microphone access required!';
                
                // Mobile-specific error messages
                if (isMobile()) {{
                    if (error.name === 'NotAllowedError') {{
                        elements.status.textContent = 'Please allow microphone access in browser settings';
                    }} else if (error.name === 'NotFoundError') {{
                        elements.status.textContent = 'No microphone found';
                    }}
                }}
                
                resetRecordingUI();
            }}
        }}
        
        // Stop recording
        function stopRecording() {{
            if (!isRecording) return;
            
            isRecording = false;
            
            // Stop media recorder
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
                mediaRecorder.stop();
            }}
            
            // Stop audio playback
            elements.accompanimentAudio.pause();
            elements.accompanimentAudio.currentTime = 0;
            
            // Stop microphone
            if (recordingStream) {{
                recordingStream.getTracks().forEach(track => track.stop());
            }}
            
            // Clear intervals
            clearInterval(progressInterval);
            
            // Update UI
            elements.status.textContent = 'Processing recording...';
        }}
        
        // Show playback section
        function showPlaybackSection() {{
            if (recordedChunks.length === 0) {{
                elements.status.textContent = 'Recording failed - no audio captured';
                resetRecordingUI();
                return;
            }}
            
            const blob = new Blob(recordedChunks, {{ type: 'audio/webm' }});
            const url = URL.createObjectURL(blob);
            
            // Store for playback and download
            window.recordingUrl = url;
            window.recordingBlob = blob;
            
            // Update UI
            elements.playbackSection.style.display = 'flex';
            elements.controls.style.display = 'none';
            elements.status.style.display = 'none';
            elements.progressContainer.style.display = 'none';
            elements.timer.style.display = 'none';
        }}
        
        // Play recording
        function playRecording() {{
            if (!window.recordingUrl) return;
            
            if (playRecordingAudio && !playRecordingAudio.paused) {{
                playRecordingAudio.pause();
                elements.playRecordingBtn.textContent = '▶ Play Recording';
            }} else {{
                if (playRecordingAudio) {{
                    playRecordingAudio.currentTime = 0;
                }}
                playRecordingAudio = new Audio(window.recordingUrl);
                playRecordingAudio.volume = 1.0;
                
                playRecordingAudio.play()
                    .then(() => {{
                        elements.playRecordingBtn.textContent = '⏸ Pause Recording';
                    }})
                    .catch(error => {{
                        console.error('Playback error:', error);
                        elements.playRecordingBtn.textContent = '▶ Play Recording';
                    }});
                
                playRecordingAudio.onended = () => {{
                    elements.playRecordingBtn.textContent = '▶ Play Recording';
                }};
            }}
        }}
        
        // Download recording
        function downloadRecording() {{
            if (!window.recordingBlob) return;
            
            const songName = '{selected_song}'.replace(/[^a-zA-Z0-9]/g, '_');
            const downloadUrl = URL.createObjectURL(window.recordingBlob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `${{songName}}_recording.webm`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            // Clean up
            setTimeout(() => URL.revokeObjectURL(downloadUrl), 100);
        }}
        
        // Start new recording
        function newRecording() {{
            // Clean up
            if (window.recordingUrl) {{
                URL.revokeObjectURL(window.recordingUrl);
                window.recordingUrl = null;
                window.recordingBlob = null;
            }}
            
            if (playRecordingAudio) {{
                playRecordingAudio.pause();
                playRecordingAudio = null;
            }}
            
            // Reset UI
            elements.playbackSection.style.display = 'none';
            elements.controls.style.display = 'block';
            elements.status.style.display = 'block';
            elements.progressContainer.style.display = 'block';
            elements.timer.style.display = 'block';
            
            resetRecordingUI();
        }}
        
        // Reset recording UI
        function resetRecordingUI() {{
            elements.recordBtn.style.display = 'block';
            elements.stopBtn.style.display = 'none';
            elements.playOriginalBtn.disabled = false;
            elements.status.textContent = 'Ready to sing! 🎤';
            elements.playOriginalBtn.textContent = '▶ Play Original';
            
            // Reset progress
            elements.progressBar.style.width = '0%';
            updateTimer(0, totalDuration);
        }}
        
        // Clean up on page unload
        window.addEventListener('beforeunload', () => {{
            if (window.recordingUrl) {{
                URL.revokeObjectURL(window.recordingUrl);
            }}
            if (audioContext) {{
                audioContext.close();
            }}
        }});
        
        // Mobile touch optimizations
        if (isMobile()) {{
            // Prevent zoom on double-tap
            document.addEventListener('touchstart', (e) => {{
                if (e.touches.length > 1) e.preventDefault();
            }}, {{ passive: false }});
            
            // Touch feedback for buttons
            document.querySelectorAll('button').forEach(btn => {{
                btn.addEventListener('touchstart', () => {{
                    btn.style.opacity = '0.8';
                }});
                
                btn.addEventListener('touchend', () => {{
                    btn.style.opacity = '1';
                }});
            }});
        }}
        
        // Initialize when page loads
        window.addEventListener('load', init);
    </script>
</body>
</html>
"""
    
    # Display the karaoke player
    html(karaoke_html, height=900, width=480, scrolling=False)

# =============== FALLBACK ===============
else:
    if "song" in st.query_params:
        st.session_state.page = "Song Player"
    else:
        st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()
