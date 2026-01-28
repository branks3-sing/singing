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
def get_audio_duration(file_path):
    """Get accurate audio duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 
            'format=duration', '-of', 
            'default=noprint_wrappers=1:nokey=1', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            if duration > 0:
                return duration
    except:
        pass
    
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(file_path)
        duration = len(audio) / 1000.0
        if duration > 0:
            return duration
    except:
        pass
    
    return 30.0

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
        subprocess.run(cmd, capture_output=True)
        return True
    except:
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
                      duration REAL)''')
        conn.commit()
        conn.close()
    except:
        pass

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
    except:
        pass

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
    except:
        pass

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
    except:
        pass

def delete_shared_link_from_db(song_name):
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('DELETE FROM shared_links WHERE song_name = ?', (song_name,))
        conn.commit()
        conn.close()
    except:
        pass

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
    except:
        pass
    return links

def save_metadata_to_db(song_name, uploaded_by, duration=None):
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
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('DELETE FROM metadata WHERE song_name = ?', (song_name,))
        conn.commit()
        conn.close()
    except:
        pass

def load_metadata_from_db():
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
        save_metadata_to_db(song_name, uploaded_by, duration)

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

# =============== GET ACCURATE AUDIO DURATION FOR SONG ===============
def get_song_duration(song_name):
    metadata = get_metadata_cached()
    
    if song_name in metadata and "duration" in metadata[song_name]:
        duration = metadata[song_name]["duration"]
        if duration and duration > 0:
            return duration
    
    acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
    if os.path.exists(acc_path):
        try:
            duration = get_audio_duration(acc_path)
            if song_name in metadata:
                metadata[song_name]["duration"] = duration
            else:
                metadata[song_name] = {"duration": duration, "uploaded_by": "unknown"}
            
            save_metadata(metadata)
            get_metadata_cached.clear()
            return duration
        except:
            pass
    
    original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
    if os.path.exists(original_path):
        try:
            duration = get_audio_duration(original_path)
            if duration > 0:
                return duration
        except:
            pass
    
    return 180

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
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    
    html, body, #root, .stApp {
        overflow: hidden !important;
        height: 100vh !important;
        width: 100vw !important;
        margin: 0 !important;
        padding: 0 !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
    }
    
    body {
        background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        overflow: hidden !important;
    }

    .login-content {
        padding: 1.8rem 2.2rem 2.2rem 2.2rem;
        max-height: 90vh;
        overflow-y: auto;
    }

    .login-header {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.8rem;
        margin-bottom: 1.6rem;
        text-align: center;
    }

    .login-header img {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        border: 2px solid rgba(255,255,255,0.4);
    }

    .login-title {
        font-size: 1.6rem;
        font-weight: 700;
        width: 100%;
    }

    .login-sub {
        font-size: 0.9rem;
        color: #c3cfdd;
        margin-bottom: 0.5rem;
        width: 100%;
    }

    .stTextInput input {
        background: rgba(5,10,25,0.7) !important;
        border-radius: 10px !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        padding: 12px 14px !important;
    }

    .stTextInput input:focus {
        border-color: rgba(255,255,255,0.6) !important;
        box-shadow: 0 0 0 1px rgba(255,255,255,0.3);
    }

    .stButton button {
        width: 100%;
        height: 44px;
        background: linear-gradient(to right, #1f2937, #020712);
        border-radius: 10px;
        font-weight: 600;
        margin-top: 0.6rem;
        color: white;
        border: none;
    }
    
    @media (max-width: 768px) {
        .login-content {
            padding: 1.5rem 1rem 1.5rem 1rem;
        }
        
        .login-header img {
            width: 50px;
            height: 50px;
        }
        
        .login-title {
            font-size: 1.4rem;
        }
        
        .stTextInput input {
            font-size: 14px !important;
            padding: 10px 12px !important;
        }
        
        .stButton button {
            font-size: 14px !important;
            height: 40px !important;
        }
        
        .stColumn {
            padding: 0 5px !important;
        }
    }
    
    @media (max-width: 480px) {
        .login-content {
            padding: 1rem 0.8rem 1rem 0.8rem;
        }
        
        .login-header img {
            width: 40px;
            height: 40px;
        }
        
        .login-title {
            font-size: 1.2rem;
        }
        
        .stTextInput input {
            font-size: 13px !important;
            padding: 8px 10px !important;
        }
        
        .stButton button {
            font-size: 13px !important;
            height: 36px !important;
        }
    }
    
    .contact-links-row {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 20px;
        margin-bottom: 15px;
    }
    
    .contact-link-item {
        text-decoration: none !important;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        font-size: 0.75rem !important;
        font-weight: 500;
        padding: 6px 10px;
        border-radius: 6px;
        transition: transform 0.2s, opacity 0.2s;
    }
    
    .contact-link-item:hover {
        transform: translateY(-1px);
        opacity: 0.9;
        text-decoration: none !important;
    }
    
    .contact-link-item.email {
        color: #4285F4 !important;
        background: rgba(66, 133, 244, 0.1);
        border: none;
    }
    
    .contact-link-item.instagram {
        background: linear-gradient(45deg, #405DE6, #5851DB, #833AB4, #C13584, #E1306C, #FD1D1D) !important;
        -webkit-background-clip: text !important;
        background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        text-fill-color: transparent !important;
        border: none;
    }
    
    .contact-link-item.youtube {
        color: #FF0000 !important;
        background: rgba(255, 0, 0, 0.1);
        border: none;
    }
    
    @media (max-width: 768px) {
        .contact-links-row {
            gap: 4px;
        }
        
        .contact-link-item {
            font-size: 0.7rem !important;
            padding: 4px 8px;
        }
    }
    
    @media (max-width: 480px) {
        .contact-links-row {
            gap: 3px;
        }
        
        .contact-link-item {
            font-size: 0.65rem !important;
            padding: 3px 6px;
        }
    }
    
    .dashboard-buttons-row {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin-top: 10px;
        margin-bottom: 5px;
    }
    
    .dashboard-button {
        font-size: 0.8rem;
        padding: 4px 12px;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        cursor: pointer;
        text-decoration: none;
        transition: all 0.2s;
    }
    
    .dashboard-button:hover {
        background: rgba(255, 255, 255, 0.2);
        text-decoration: none;
    }
    </style>
    """, unsafe_allow_html=True)

    left, center, right = st.columns([0.5, 2, 0.5])

    with center:
        st.markdown('<div class="login-content">', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="login-header">
            <img src="data:image/png;base64,{logo_b64}" onerror="this.style.display='none'">
            <div class="login-title">𝄞 Sing Along</div>
            <div class="login-sub">Login to continue</div>
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="Enter user name", value="", key="login_username")
        password = st.text_input("Password", type="password", placeholder="Enter password", value="", key="login_password")

        if st.button("Login", key="login_button"):
            if not username or not password:
                st.error("❌ Enter both username and password")
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
                    st.error("❌ Invalid credentials")

        st.markdown("""
        <div style="margin-top:16px;font-size:0.8rem;color:#b5c2d2;text-align:center;padding-bottom:8px;">
            Don't have access? Contact admin:
        </div>
        <div class="contact-links-row">
            <a href="mailto:branks3.singalong@gmail.com" 
               class="contact-link-item email"
               target="_blank">
               📧 Email
            </a>
            <a href="https://www.instagram.com/branks3.sing_along/" 
               class="contact-link-item instagram"
               target="_blank">
               🅾 Instagram
            </a>
            <a href="https://www.youtube.com/@branks3.sing_along" 
               class="contact-link-item youtube"
               target="_blank">
               ▶ YouTube
            </a>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    save_session_to_db()
    
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        h1 {
            font-size: 1.5rem !important;
        }
        
        h3 {
            font-size: 1.2rem !important;
        }
        
        .stButton > button {
            font-size: 14px !important;
            padding: 8px 12px !important;
        }
        
        .stRadio > div[role="radiogroup"] > label {
            font-size: 14px !important;
        }
        
        [data-testid="stSidebar"] * {
            font-size: 14px !important;
        }
        
        .song-name {
            font-size: 14px !important;
        }
        
        .stColumn {
            padding: 2px !important;
        }
        
        .stTextInput > div > div > input {
            font-size: 14px !important;
            padding: 8px !important;
        }
        
        .stFileUploader > div {
            font-size: 12px !important;
        }
        
        .main .block-container {
            padding: 1rem !important;
        }
    }
    
    @media (max-width: 480px) {
        h1 {
            font-size: 1.3rem !important;
        }
        
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
        
        .stRadio > div[role="radiogroup"] > label {
            font-size: 12px !important;
        }
        
        .stColumn {
            width: 100% !important;
            padding: 0 !important;
            margin-bottom: 10px !important;
        }
    }
    
    .delete-button {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        min-width: auto !important;
        width: auto !important;
        color: #ff4444 !important;
        font-size: 20px !important;
        box-shadow: none !important;
    }
    
    .delete-button:hover {
        background: transparent !important;
        color: #ff0000 !important;
        transform: scale(1.1);
    }
    
    .song-item-row {
        display: flex;
        align-items: center;
        margin-bottom: 4px !important;
        padding: 0 !important;
        background: transparent !important;
    }
    
    .play-button {
        background: transparent !important;
        border: none !important;
        color: #4CAF50 !important;
        text-align: left !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 100% !important;
    }
    
    .play-button:hover {
        background: rgba(76, 175, 80, 0.1) !important;
    }
    
    .share-link-button {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        min-width: auto !important;
        width: auto !important;
        color: #667eea !important;
        font-size: 20px !important;
    }
    
    .share-link-button:hover {
        color: #764ba2 !important;
        transform: scale(1.1);
    }
    
    @media (max-width: 768px) {
        .song-item-row {
            flex-direction: column;
            align-items: flex-start;
            margin-bottom: 10px !important;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 10px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")

    page_sidebar = st.sidebar.radio(
        "Navigate",
        ["Upload Songs", "Songs List", "Share Links"],
        key="admin_nav"
    )

    if page_sidebar == "Upload Songs":
        st.subheader("📤 Upload New Song")

        song_name_input = st.text_input(
            "🎶 Song Name",
            placeholder="Enter song name (example: MySong)",
            key="song_name_input"
        )

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
                "Lyrics Image (_lyrics_bg.jpg / .png)",
                type=["jpg", "jpeg", ".png"],
                key="lyrics_upload"
            )

        if st.button("⬆ Upload Song", key="upload_song_btn"):
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

                with open(original_path, "wb") as f:
                    f.write(uploaded_original.getbuffer())
                with open(acc_path, "wb") as f:
                    f.write(uploaded_accompaniment.getbuffer())
                with open(lyrics_path, "wb") as f:
                    f.write(uploaded_lyrics_image.getbuffer())
                
                try:
                    fix_audio_duration(original_path, original_path)
                    fix_audio_duration(acc_path, acc_path)
                except:
                    pass
                
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

    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs List (Admin View)")
        
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
            for idx, s in enumerate(uploaded_songs):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    duration = get_song_duration(s)
                    duration_text = f" [{int(duration//60)}:{int(duration%60):02d}]"
                    
                    if st.button(
                        f"🎶 {s}{duration_text}",
                        key=f"song_name_{s}_{idx}",
                        help="Click to play song",
                        use_container_width=True,
                        type="secondary"
                    ):
                        open_song_player(s)
                
                with col2:
                    safe_s = quote(s)
                    share_url = f"{APP_URL}?song={safe_s}"
                    if st.button(
                        "🔗",
                        key=f"share_icon_{s}_{idx}",
                        help="Share link"
                    ):
                        st.markdown(f"Share URL: {share_url}")
                        st.info("Link copied to clipboard!")
                
                with col3:
                    if st.button(
                        "🗑️",
                        key=f"delete_{s}_{idx}",
                        help="Delete song"
                    ):
                        st.session_state.confirm_delete = s
                        st.rerun()
            
            if st.session_state.confirm_delete:
                song_to_delete = st.session_state.confirm_delete
                st.warning(f"⚠️ Are you sure you want to delete **{song_to_delete}**?")
                
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✅ Yes, Delete", type="primary"):
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
                    if st.button("❌ Cancel", type="secondary"):
                        st.session_state.confirm_delete = None
                        st.rerun()

    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")

        all_songs = get_song_files_cached()
        
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
            for song in all_songs:
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    safe_song = quote(song)
                    is_shared = song in shared_links_data
                    status = "✅ SHARED" if is_shared else "❌ NOT SHARED"
                    st.write(f"**{song}** - {status}")
                
                with col2:
                    col_toggle, col_action = st.columns(2)
                    
                    with col_toggle:
                        if is_shared:
                            if st.button("🚫", key=f"unshare_{song}", help="Unshare"):
                                delete_shared_link(song)
                                get_shared_links_cached.clear()
                                st.success(f"✅ {song} unshared!")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            if st.button("🔗", key=f"share_{song}", help="Share"):
                                save_shared_link(
                                    song,
                                    {"shared_by": st.session_state.user, "active": True}
                                )
                                get_shared_links_cached.clear()
                                share_url = f"{APP_URL}?song={safe_song}"
                                st.success(f"✅ {song} shared!\n{share_url}")
                                time.sleep(0.5)
                                st.rerun()
                    
                    with col_action:
                        if is_shared:
                            share_url = f"{APP_URL}?song={safe_song}"
                            st.markdown(f"""
                            <a href="{share_url}" target="_blank" style="
                                display: inline-block;
                                width: 40px;
                                height: 32px;
                                background: transparent;
                                color: #667eea;
                                text-align: center;
                                line-height: 32px;
                                border-radius: 4px;
                                text-decoration: none;
                                font-size: 16px;
                                float: right;
                            " title="Open Link">🔗</a>
                            """, unsafe_allow_html=True)

    if st.sidebar.button("Logout", key="admin_logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
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
        st.markdown("<h2 style='text-align: center;'>🎵 User Dashboard</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown("### Quick Actions")
        
        if st.button("🔄 Refresh Songs List", key="user_refresh"):
            get_song_files_cached.clear()
            get_shared_links_cached.clear()
            st.rerun()
            
        if st.button("Logout", key="user_sidebar_logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()

    st.subheader("🎵 Available Songs (Only Shared Songs)")
    
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
        for idx, song in enumerate(uploaded_songs):
            duration = get_song_duration(song)
            duration_text = f" [{int(duration//60)}:{int(duration%60):02d}]"
            
            if st.button(
                f"✅ *{song}*{duration_text}",
                key=f"user_song_{song}_{idx}",
                help="Click to play song",
                use_container_width=True,
                type="secondary"
            ):
                open_song_player(song)

# =============== SONG PLAYER WITH FIXED RECORDING ===============
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
    
    song_duration = get_song_duration(selected_song)

    # ✅ FIXED KARAOKE TEMPLATE WITH CLEAR RECORDING
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
  </style>
</head>
<body>
  <div class="karaoke-wrapper" id="karaokeWrapper">
      <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%" onerror="this.style.display='none'">
      <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%" onerror="this.style.display='none'">
      <div id="status">Ready 🎤 Tap screen first</div>
      <audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%" preload="auto"></audio>
      <audio id="accompaniment" src="data:audio/mp3;base64,%%ACCOMP_B64%%" preload="auto"></audio>
      <div class="controls">
        <button id="playBtn">▶ Play Song</button>
        <button id="recordBtn">🎙 Start Recording</button>
        <button id="stopBtn" style="display:none;">⏹ Stop Recording</button>
      </div>
  </div>

  <div class="final-output" id="finalOutputDiv">
    <div class="karaoke-wrapper">
      <img class="reel-bg" id="finalBg">
      <div id="finalStatus">Recording Complete!</div>
      <div class="controls">
        <button id="playRecordingBtn">▶ Play Recording</button>
        <a id="downloadRecordingBtn" href="#" download>
          <button>⬇ Download</button>
        </a>
        <button id="newRecordingBtn">New Recording</button>
      </div>
    </div>
  </div>

  <canvas id="recordingCanvas"></canvas>

  <script>
  /* ================== GLOBAL STATE ================== */
  let mediaRecorder;
  let recordedChunks = [];
  let playRecordingAudio = null;
  let lastRecordingURL = null;
  let audioContext, micSource, accSource, micGain, accGain;
  let canvasRafId = null;
  let isRecording = false;
  let isPlayingRecording = false;
  let autoStopTimer = null;
  let originalAudioElement = null;

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

  /* ================== CANVAS SETUP ================== */
  canvas.width = 360;
  canvas.height = 640;

  /* ================== AUDIO CONTEXT FIX ================== */
  async function ensureAudioContext() {
      if (!audioContext) {
          audioContext = new (window.AudioContext || window.webkitAudioContext)({
              sampleRate: 44100,
              latencyHint: 'interactive'
          });
      }
      if (audioContext.state === "suspended") {
          await audioContext.resume();
      }
      return audioContext;
  }

  /* ================== PLAY ORIGINAL SONG ================== */
  playBtn.onclick = async function() {
      await ensureAudioContext();
      if (originalAudio.paused) {
          originalAudio.currentTime = 0;
          originalAudio.play().then(() => {
              playBtn.innerText = "⏹ Stop Song";
              status.innerText = "🎵 Playing original song...";
          }).catch(e => {
              console.log("Play error:", e);
              status.innerText = "❌ Tap screen first";
          });
      } else {
          originalAudio.pause();
          originalAudio.currentTime = 0;
          playBtn.innerText = "▶ Play Song";
          status.innerText = "⏹ Stopped";
      }
  };

  /* ================== CANVAS DRAW ================== */
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

      ctx.drawImage(mainBg, x, y, drawW, drawH);
      
      const logoSize = 30;
      ctx.drawImage(logoImg, 10, 10, logoSize, logoSize);

      canvasRafId = requestAnimationFrame(drawCanvas);
  }

  /* ================== FIXED RECORDING FUNCTION ================== */
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
          
          // IMPORTANT: Play original song for reference ONLY (NOT recorded)
          // This plays separately and will NOT be included in recording
          originalAudio.currentTime = 0;
          originalAudio.play().catch(e => {
              console.log("Original song play error:", e);
          });
          
          // Get microphone with OPTIMIZED settings for clarity
          const micStream = await navigator.mediaDevices.getUserMedia({
              audio: {
                  echoCancellation: true,      // Reduced echo
                  noiseSuppression: true,      // Better noise cancellation
                  autoGainControl: true,       // Automatic volume control
                  channelCount: 1,             // Mono for better compatibility
                  sampleRate: 44100,           // High quality
                  sampleSize: 16               // 16-bit for clarity
              },
              video: false
          }).catch(err => {
              status.innerText = "❌ Microphone access required";
              resetUIOnError();
              throw err;
          });
          
          // Create microphone source
          micSource = audioCtx.createMediaStreamSource(micStream);
          
          // Load accompaniment for recording
          const accRes = await fetch(accompanimentAudio.src);
          const accBuf = await accRes.arrayBuffer();
          const accDecoded = await audioCtx.decodeAudioData(accBuf);
          
          accSource = audioCtx.createBufferSource();
          accSource.buffer = accDecoded;
          const songDuration = %%SONG_DURATION%% * 1000;
          
          // Create gain nodes with OPTIMIZED settings
          micGain = audioCtx.createGain();
          micGain.gain.value = 1.8;  // Optimized for voice clarity
          
          accGain = audioCtx.createGain();
          accGain.gain.value = 0.4;  // Background music level
          
          // Create destination for recording - ONLY microphone + accompaniment
          const destination = audioCtx.createMediaStreamDestination();
          
          // Connect ONLY microphone and accompaniment to recording
          micSource.connect(micGain);
          micGain.connect(destination);
          accSource.connect(accGain);
          accGain.connect(destination);
          
          // Start canvas drawing for video
          drawCanvas();
          
          // Start accompaniment for recording
          accSource.start();
          
          // Create stream from canvas and mixed audio
          const canvasStream = canvas.captureStream(30);
          const mixedAudioStream = destination.stream;
          
          // Combine video and audio streams
          // ORIGINAL SONG IS NOT INCLUDED HERE
          const combinedStream = new MediaStream([
              ...canvasStream.getVideoTracks(),
              ...mixedAudioStream.getAudioTracks()
          ]);
          
          // Use WebM with Opus for best quality
          let mimeType = 'video/webm;codecs=vp9,opus';
          if (!MediaRecorder.isTypeSupported(mimeType)) {
              mimeType = 'video/webm;codecs=vp8,opus';
          }
          
          // Create MediaRecorder with OPTIMIZED settings
          mediaRecorder = new MediaRecorder(combinedStream, {
              mimeType: mimeType,
              audioBitsPerSecond: 192000,     // Higher quality audio
              videoBitsPerSecond: 3000000,    // Higher quality video
              videoKeyFrameInterval: 30       // Smoother video
          });
          
          recordedChunks = [];
          mediaRecorder.ondataavailable = e => {
              if (e.data.size > 0) {
                  recordedChunks.push(e.data);
              }
          };
          
          mediaRecorder.onstop = () => {
              cancelAnimationFrame(canvasRafId);
              
              // Stop all audio sources
              if (accSource) {
                  try { 
                      accSource.stop(); 
                      accSource.disconnect();
                  } catch(e) {}
                  accSource = null;
              }
              
              if (micSource) {
                  try { 
                      micSource.disconnect(); 
                  } catch(e) {}
                  micSource = null;
              }
              
              // Stop original song
              originalAudio.pause();
              originalAudio.currentTime = 0;
              
              // Create blob
              if (recordedChunks.length > 0) {
                  const blob = new Blob(recordedChunks, { type: mimeType });
                  const url = URL.createObjectURL(blob);
                  
                  if (lastRecordingURL) URL.revokeObjectURL(lastRecordingURL);
                  lastRecordingURL = url;
                  
                  finalBg.src = mainBg.src;
                  finalDiv.style.display = "flex";
                  finalStatus.innerText = "✅ Recording Complete!";
                  
                  // Set download link
                  const songName = "%%SONG_NAME%%".replace(/[^a-zA-Z0-9]/g, '_');
                  const extension = '.webm';
                  const fileName = songName + "_karaoke_recording" + extension;
                  downloadRecordingBtn.href = url;
                  downloadRecordingBtn.download = fileName;
                  
                  // Playback button
                  playRecordingBtn.onclick = () => {
                      if (!isPlayingRecording) {
                          if (playRecordingAudio) {
                              playRecordingAudio.pause();
                              playRecordingAudio = null;
                          }
                          playRecordingAudio = new Audio(url);
                          playRecordingAudio.volume = 1.0;
                          playRecordingAudio.play();
                          playRecordingBtn.innerText = "⏹ Stop";
                          isPlayingRecording = true;
                          
                          playRecordingAudio.onended = () => {
                              playRecordingBtn.innerText = "▶ Play Recording";
                              isPlayingRecording = false;
                          };
                      } else {
                          if (playRecordingAudio) {
                              playRecordingAudio.pause();
                              playRecordingAudio.currentTime = 0;
                          }
                          playRecordingBtn.innerText = "▶ Play Recording";
                          isPlayingRecording = false;
                      }
                  };
              }
          };
          
          // Start recording with optimized chunk size
          mediaRecorder.start(500); // Smaller chunks for smoother recording
          
          status.innerText = "🎙 Recording... Original song playing (NOT recorded)";
          
          // Auto-stop timer based on actual song duration
          autoStopTimer = setTimeout(() => {
              if (isRecording) {
                  stopRecording();
                  status.innerText = "✅ Auto-stopped: Recording complete!";
              }
          }, songDuration + 1000);
          
      } catch (error) {
          console.error("Recording error:", error);
          status.innerText = "❌ Failed: " + (error.message || "Check microphone access");
          resetUIOnError();
      }
  };

  /* ================== STOP RECORDING ================== */
  function stopRecording() {
      if (!isRecording) return;
      
      // Clear timer
      if (autoStopTimer) {
          clearTimeout(autoStopTimer);
          autoStopTimer = null;
      }
      
      // Stop media recorder
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
          mediaRecorder.stop();
      }
      
      // Stop audio sources
      if (accSource) {
          try { 
              accSource.stop(); 
              accSource.disconnect();
          } catch(e) {}
      }
      
      if (micSource) {
          try { 
              micSource.disconnect(); 
          } catch(e) {}
      }
      
      // Stop original song
      originalAudio.pause();
      originalAudio.currentTime = 0;
      
      // Stop canvas
      if (canvasRafId) {
          cancelAnimationFrame(canvasRafId);
          canvasRafId = null;
      }
      
      // Update UI
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
      finalDiv.style.display = "none";
      
      // Cleanup
      if (playRecordingAudio) {
          playRecordingAudio.pause();
          playRecordingAudio = null;
      }
      
      // Reset audio
      originalAudio.pause();
      originalAudio.currentTime = 0;
      
      // Reset UI
      playBtn.style.display = "inline-block";
      recordBtn.style.display = "inline-block";
      stopBtn.style.display = "none";
      playBtn.innerText = "▶ Play Song";
      status.innerText = "Ready 🎤";
      
      // Reset state
      recordedChunks = [];
      isRecording = false;
      isPlayingRecording = false;
      
      // Release URL
      if (lastRecordingURL) {
          URL.revokeObjectURL(lastRecordingURL);
          lastRecordingURL = null;
      }
      
      // Clear audio context
      if (audioContext) {
          try {
              audioContext.close();
          } catch(e) {}
          audioContext = null;
      }
  };

  /* ================== HELPER FUNCTIONS ================== */
  function resetUIOnError() {
      isRecording = false;
      playBtn.style.display = "inline-block";
      recordBtn.style.display = "inline-block";
      stopBtn.style.display = "none";
      playBtn.innerText = "▶ Play Song";
      
      // Stop original song
      originalAudio.pause();
      originalAudio.currentTime = 0;
      
      if (autoStopTimer) {
          clearTimeout(autoStopTimer);
          autoStopTimer = null;
      }
  }

  /* ================== TOUCH EVENTS FOR MOBILE ================== */
  document.addEventListener('touchstart', async () => {
      await ensureAudioContext();
  }, { once: true });

  /* ================== INITIALIZE ================== */
  window.addEventListener('load', () => {
      status.innerText = "Ready 🎤 - Tap screen first";
  });

  /* ================== CLEANUP ================== */
  window.addEventListener('beforeunload', () => {
      if (lastRecordingURL) {
          URL.revokeObjectURL(lastRecordingURL);
      }
      if (audioContext) {
          audioContext.close();
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

    # Display karaoke player
    html(f'<div class="karaoke-container">{karaoke_html}</div>', height=640, width=360, scrolling=False)

# =============== FALLBACK ===============
else:
    if "song" in st.query_params:
        st.session_state.page = "Song Player"
    else:
        st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()
