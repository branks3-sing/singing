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

# =============== MOBILE DETECTION AND RESPONSIVE SETUP ===============
def is_mobile():
    """Detect if user is on mobile device"""
    user_agent = st.query_params.get("ua", "")
    if not user_agent:
        # Try to get from headers (won't work in Streamlit directly)
        return False
    
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 
                      'blackberry', 'windows phone', 'opera mini']
    
    user_agent_lower = user_agent.lower()
    for keyword in mobile_keywords:
        if keyword in user_agent_lower:
            return True
    return False

# Set responsive page config with mobile optimization
st.set_page_config(
    page_title="Sing Along",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============== RESPONSIVE CSS FOR ALL DEVICES ===============
RESPONSIVE_CSS = """
<style>
/* Base responsive styles */
* {
    box-sizing: border-box;
}

/* Mobile-first responsive design */
@media (max-width: 768px) {
    /* Adjust main container for mobile */
    .main .block-container {
        padding: 1rem 0.5rem !important;
        max-width: 100% !important;
    }
    
    /* Header adjustments */
    h1 {
        font-size: 1.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    h2 {
        font-size: 1.3rem !important;
    }
    
    h3 {
        font-size: 1.1rem !important;
    }
    
    /* Button adjustments */
    .stButton > button {
        font-size: 14px !important;
        padding: 8px 12px !important;
        width: 100% !important;
        margin: 4px 0 !important;
    }
    
    /* Input adjustments */
    .stTextInput > div > div > input {
        font-size: 14px !important;
        padding: 10px 12px !important;
    }
    
    /* Text area adjustments */
    .stTextArea > div > div > textarea {
        font-size: 14px !important;
    }
    
    /* Radio button adjustments */
    .stRadio > div {
        flex-direction: column !important;
    }
    
    .stRadio > div > label {
        font-size: 14px !important;
        margin-bottom: 5px !important;
    }
    
    /* Column adjustments */
    .stColumn {
        padding: 0 4px !important;
        margin-bottom: 10px !important;
    }
    
    /* File uploader adjustments */
    .stFileUploader > div {
        font-size: 12px !important;
    }
    
    /* Song list items */
    .song-item {
        padding: 10px !important;
        margin: 5px 0 !important;
        font-size: 14px !important;
    }
    
    /* Table adjustments */
    .stDataFrame {
        font-size: 12px !important;
    }
    
    /* Sidebar adjustments */
    [data-testid="stSidebar"] {
        min-width: 200px !important;
        max-width: 280px !important;
    }
    
    /* Hide sidebar on mobile by default */
    [data-testid="stSidebar"][aria-expanded="true"] {
        width: 100% !important;
        max-width: 100% !important;
    }
}

/* Ultra small mobile devices */
@media (max-width: 480px) {
    .main .block-container {
        padding: 0.5rem !important;
    }
    
    h1 {
        font-size: 1.3rem !important;
    }
    
    h2 {
        font-size: 1.1rem !important;
    }
    
    h3 {
        font-size: 1rem !important;
    }
    
    .stButton > button {
        font-size: 12px !important;
        padding: 6px 10px !important;
    }
    
    .stTextInput > div > div > input {
        font-size: 12px !important;
        padding: 8px 10px !important;
    }
    
    .song-item {
        padding: 8px !important;
        font-size: 12px !important;
    }
    
    /* Stack columns vertically */
    .stHorizontalBlock > div {
        width: 100% !important;
        display: block !important;
    }
    
    /* Adjust column spacing */
    .stColumn {
        width: 100% !important;
        padding: 0 !important;
        margin-bottom: 15px !important;
    }
}

/* Tablet devices */
@media (min-width: 769px) and (max-width: 1024px) {
    .main .block-container {
        padding: 1.5rem !important;
    }
    
    .stButton > button {
        font-size: 15px !important;
        padding: 10px 15px !important;
    }
}

/* 9:16 Aspect Ratio Specific Styles */
@media (max-aspect-ratio: 9/16) {
    /* Full screen mode for ultra-tall screens */
    .stApp {
        max-height: 100vh !important;
        overflow-y: auto !important;
    }
    
    .main .block-container {
        padding: 0.5rem !important;
        min-height: calc(100vh - 60px) !important;
    }
    
    /* Compact song list for tall screens */
    .song-list-container {
        max-height: 60vh !important;
        overflow-y: auto !important;
    }
    
    /* Smaller headers for tall screens */
    h1 {
        font-size: 1.2rem !important;
        margin-bottom: 0.3rem !important;
    }
    
    /* Compact buttons */
    .stButton > button {
        padding: 6px 8px !important;
        margin: 2px 0 !important;
        min-height: 36px !important;
    }
    
    /* Hide unnecessary elements on tall screens */
    .mobile-hide {
        display: none !important;
    }
}

/* Landscape mode */
@media (orientation: landscape) and (max-height: 600px) {
    /* Adjust for landscape mobile */
    .main .block-container {
        padding: 0.3rem !important;
    }
    
    /* Make everything more compact in landscape */
    .compact-mode * {
        font-size: 90% !important;
    }
}

/* Common responsive utilities */
.responsive-col {
    width: 100% !important;
    margin-bottom: 10px !important;
}

.mobile-stack {
    display: flex !important;
    flex-direction: column !important;
}

.mobile-center {
    text-align: center !important;
}

.mobile-full-width {
    width: 100% !important;
    max-width: 100% !important;
}

/* Song player specific responsive styles */
.song-player-container {
    width: 100% !important;
    height: 100% !important;
    max-width: 100vw !important;
    max-height: 100vh !important;
}

/* Login page responsive */
.login-container {
    max-width: 400px !important;
    margin: 0 auto !important;
}

@media (max-width: 480px) {
    .login-container {
        max-width: 100% !important;
        padding: 1rem !important;
    }
}

/* Scrollbar styling for mobile */
::-webkit-scrollbar {
    width: 4px;
    height: 4px;
}

::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 2px;
}

::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 2px;
}

::-webkit-scrollbar-thumb:hover {
    background: #555;
}

/* Touch-friendly buttons */
.touch-button {
    min-height: 44px !important; /* Apple's recommended minimum touch target */
    min-width: 44px !important;
}

/* Prevent text selection on mobile */
.no-select {
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
}

/* Loading spinner responsive */
.stSpinner > div {
    width: 30px !important;
    height: 30px !important;
}

@media (max-width: 480px) {
    .stSpinner > div {
        width: 20px !important;
        height: 20px !important;
    }
}

/* Alert/Toast messages */
.stAlert {
    font-size: 14px !important;
    padding: 10px !important;
}

@media (max-width: 480px) {
    .stAlert {
        font-size: 12px !important;
        padding: 8px !important;
    }
}

/* Success message */
.stSuccess {
    background-color: rgba(0, 200, 83, 0.1) !important;
    border-left: 4px solid #00c853 !important;
}

/* Error message */
.stError {
    background-color: rgba(255, 23, 68, 0.1) !important;
    border-left: 4px solid #ff1744 !important;
}

/* Warning message */
.stWarning {
    background-color: rgba(255, 193, 7, 0.1) !important;
    border-left: 4px solid #ffc107 !important;
}

/* Info message */
.stInfo {
    background-color: rgba(3, 169, 244, 0.1) !important;
    border-left: 4px solid #03a9f4 !important;
}

/* Dashboard specific responsive */
.dashboard-grid {
    display: grid !important;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)) !important;
    gap: 15px !important;
}

@media (max-width: 768px) {
    .dashboard-grid {
        grid-template-columns: 1fr !important;
        gap: 10px !important;
    }
}

/* Card style for dashboard items */
.dashboard-card {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    background: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

@media (max-width: 768px) {
    .dashboard-card {
        padding: 10px;
    }
}

/* Hide sidebar toggle on mobile */
@media (max-width: 768px) {
    [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
}

/* Mobile menu button */
.mobile-menu-btn {
    position: fixed !important;
    top: 10px !important;
    right: 10px !important;
    z-index: 1000 !important;
    background: white !important;
    border-radius: 50% !important;
    width: 40px !important;
    height: 40px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2) !important;
}

/* Footer responsive */
.footer {
    font-size: 12px !important;
    padding: 10px !important;
    text-align: center !important;
    margin-top: auto !important;
}

@media (max-width: 480px) {
    .footer {
        font-size: 10px !important;
        padding: 5px !important;
    }
}

/* Ensure images are responsive */
img {
    max-width: 100% !important;
    height: auto !important;
}

/* Video/audio player responsive */
audio, video {
    width: 100% !important;
    max-width: 100% !important;
}

/* Form elements responsive */
select, textarea, input[type="text"], input[type="password"], input[type="email"], input[type="number"] {
    font-size: 16px !important; /* Prevents iOS zoom */
    max-width: 100% !important;
}

@media (max-width: 768px) {
    select, textarea, input[type="text"], input[type="password"], input[type="email"], input[type="number"] {
        font-size: 14px !important;
    }
}

/* Prevent horizontal scrolling */
body {
    overflow-x: hidden !important;
    max-width: 100vw !important;
}

/* Streamlit specific overrides */
div[data-testid="stVerticalBlock"] {
    gap: 0.5rem !important;
}

@media (max-width: 768px) {
    div[data-testid="stVerticalBlock"] {
        gap: 0.3rem !important;
    }
}

/* Custom responsive container */
.responsive-container {
    width: 100% !important;
    padding-right: 15px !important;
    padding-left: 15px !important;
    margin-right: auto !important;
    margin-left: auto !important;
}

@media (min-width: 576px) {
    .responsive-container {
        max-width: 540px !important;
    }
}

@media (min-width: 768px) {
    .responsive-container {
        max-width: 720px !important;
    }
}

@media (min-width: 992px) {
    .responsive-container {
        max-width: 960px !important;
    }
}

@media (min-width: 1200px) {
    .responsive-container {
        max-width: 1140px !important;
    }
}

/* Mobile-specific helper classes */
.mobile-only {
    display: none !important;
}

.desktop-only {
    display: block !important;
}

@media (max-width: 768px) {
    .mobile-only {
        display: block !important;
    }
    
    .desktop-only {
        display: none !important;
    }
}

/* Animation for mobile interactions */
.mobile-tap-feedback:active {
    opacity: 0.7 !important;
    transform: scale(0.98) !important;
    transition: all 0.1s ease !important;
}

/* Safe area insets for notched phones */
@supports (padding: max(0px)) {
    .safe-area-top {
        padding-top: max(15px, env(safe-area-inset-top)) !important;
    }
    
    .safe-area-bottom {
        padding-bottom: max(15px, env(safe-area-inset-bottom)) !important;
    }
    
    .safe-area-left {
        padding-left: max(15px, env(safe-area-inset-left)) !important;
    }
    
    .safe-area-right {
        padding-right: max(15px, env(safe-area-inset-right)) !important;
    }
}
</style>
"""

# Apply responsive CSS
st.markdown(RESPONSIVE_CSS, unsafe_allow_html=True)

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
    page_icon = "🎤"

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

# =============== RESPONSIVE HELPER FUNCTIONS ===============
def get_responsive_columns(col_sizes_desktop, col_sizes_mobile=None):
    """Get responsive column configuration based on screen size"""
    if col_sizes_mobile is None:
        col_sizes_mobile = [1] * len(col_sizes_desktop)  # Default to equal columns
    
    # For now, we'll use mobile if we detect mobile user agent
    # In a real implementation, you'd use JavaScript to detect screen width
    use_mobile = st.session_state.get('mobile_mode', False)
    
    if use_mobile:
        return st.columns(col_sizes_mobile)
    else:
        return st.columns(col_sizes_desktop)

def responsive_button(text, key, type="secondary", use_container_width=None):
    """Create a responsive button that adapts to screen size"""
    if use_container_width is None:
        # Auto-detect based on mobile mode
        use_container_width = st.session_state.get('mobile_mode', False)
    
    return st.button(
        text,
        key=key,
        type=type,
        use_container_width=use_container_width
    )

def responsive_text_input(label, placeholder="", key=None, value=""):
    """Create responsive text input"""
    return st.text_input(
        label,
        placeholder=placeholder,
        key=key,
        value=value
    )

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
    
    # Calculate duration
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
    # Try to detect mobile mode
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
    pass
logo_b64 = file_to_base64(default_logo_path) if os.path.exists(default_logo_path) else ""

# =============== RESPONSIVE LOGIN PAGE (NO SCROLLING) ===============
if st.session_state.page == "Login":
    save_session_to_db()
    
    st.markdown("""
    <style>
    /* Login page specific responsive styles */
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 20px;
    }
    
    @media (max-width: 480px) {
        .login-container {
            padding: 15px;
            max-width: 100%;
        }
    }
    
    /* Mobile touch optimization */
    .touch-optimized {
        min-height: 44px;
        padding: 12px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Responsive login layout
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Responsive header
        col1, col2, col3 = get_responsive_columns([1, 2, 1], [0.2, 3, 0.2])
        
        with col2:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="font-size: 2rem; color: white; margin-bottom: 10px;">🎤 Sing Along</h1>
                <p style="color: #aaa; font-size: 1rem;">Login to continue</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Responsive form
            username = responsive_text_input("👤 Username", placeholder="Enter user name", key="login_username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter password", key="login_password")
            
            # Responsive login button
            if responsive_button("🚪 Login", key="login_button", type="primary", use_container_width=True):
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
            
            # Responsive contact links
            st.markdown("""
            <div style="margin-top: 30px; text-align: center;">
                <p style="color: #aaa; font-size: 0.9rem; margin-bottom: 15px;">Don't have access? Contact admin:</p>
                <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
                    <a href="mailto:branks3.singalong@gmail.com" 
                       style="padding: 8px 15px; background: #4285F4; color: white; border-radius: 5px; text-decoration: none; font-size: 0.9rem;">
                       📧 Email
                    </a>
                    <a href="https://www.instagram.com/branks3.sing_along/" 
                       style="padding: 8px 15px; background: linear-gradient(45deg, #405DE6, #C13584); color: white; border-radius: 5px; text-decoration: none; font-size: 0.9rem;">
                       🅾 Instagram
                    </a>
                    <a href="https://www.youtube.com/@branks3.sing_along" 
                       style="padding: 8px 15px; background: #FF0000; color: white; border-radius: 5px; text-decoration: none; font-size: 0.9rem;">
                       ▶ YouTube
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# =============== RESPONSIVE ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    save_session_to_db()
    
    st.title(f"👑 Admin Dashboard")
    st.markdown(f"*Logged in as: {st.session_state.user}*")
    
    # Responsive sidebar
    with st.sidebar:
        st.markdown("### 📊 Navigation")
        page_sidebar = st.radio(
            "Go to",
            ["📤 Upload Songs", "🎵 Songs List", "🔗 Share Links"],
            key="admin_nav"
        )
        
        st.markdown("---")
        
        # Responsive logout button
        if responsive_button("🚪 Logout", key="admin_logout", type="secondary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()

    # ================= RESPONSIVE UPLOAD SONGS =================
    if page_sidebar == "📤 Upload Songs":
        st.subheader("📤 Upload New Song")
        
        # Responsive form layout
        song_name_input = responsive_text_input(
            "🎶 Song Name",
            placeholder="Enter song name (example: MySong)",
            key="song_name_input"
        )
        
        # Responsive file uploaders - stacked on mobile
        if st.session_state.get('mobile_mode', False):
            # Stack vertically on mobile
            with st.container():
                st.markdown("### Original Song")
                uploaded_original = st.file_uploader(
                    "Upload original song (_original.mp3)",
                    type=["mp3"],
                    key="original_upload",
                    label_visibility="collapsed"
                )
            
            with st.container():
                st.markdown("### Accompaniment")
                uploaded_accompaniment = st.file_uploader(
                    "Upload accompaniment (_accompaniment.mp3)",
                    type=["mp3"],
                    key="acc_upload",
                    label_visibility="collapsed"
                )
            
            with st.container():
                st.markdown("### Lyrics Image")
                uploaded_lyrics_image = st.file_uploader(
                    "Upload lyrics image (_lyrics_bg.jpg/.png)",
                    type=["jpg", "jpeg", "png"],
                    key="lyrics_upload",
                    label_visibility="collapsed"
                )
        else:
            # Horizontal layout on desktop
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
                    "Lyrics Image (_lyrics_bg.jpg/.png)",
                    type=["jpg", "jpeg", "png"],
                    key="lyrics_upload"
                )
        
        # Responsive upload button
        if responsive_button("⬆ Upload Song", key="upload_song_btn", type="primary", use_container_width=st.session_state.get('mobile_mode', False)):
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

    # ================= RESPONSIVE SONGS LIST =================
    elif page_sidebar == "🎵 Songs List":
        st.subheader("🎵 All Songs List")
        
        # Responsive search
        search_query = responsive_text_input(
            "🔍 Search songs...",
            placeholder="Type song name to search",
            key="admin_search",
            value=st.session_state.get("search_query", "")
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
            # Responsive song list
            for idx, song in enumerate(uploaded_songs):
                duration = get_song_duration(song)
                duration_text = f" [{int(duration//60)}:{int(duration%60):02d}]"
                
                if st.session_state.get('mobile_mode', False):
                    # Mobile layout - stacked
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if responsive_button(
                                f"🎶 {song}{duration_text}",
                                key=f"play_{song}_{idx}",
                                type="secondary",
                                use_container_width=True
                            ):
                                open_song_player(song)
                        
                        with col2:
                            col_delete, col_share = st.columns(2)
                            with col_delete:
                                if st.button("🗑️", key=f"delete_{song}_{idx}", help="Delete song"):
                                    st.session_state.confirm_delete = song
                                    st.rerun()
                            with col_share:
                                safe_s = quote(song)
                                share_url = f"{APP_URL}?song={safe_s}"
                                if st.button("🔗", key=f"share_{song}_{idx}", help="Share link"):
                                    st.code(share_url, language="text")
                                    st.info("Link copied to clipboard!")
                else:
                    # Desktop layout - horizontal
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        if responsive_button(
                            f"🎶 {song}{duration_text}",
                            key=f"play_{song}_{idx}",
                            type="secondary",
                            use_container_width=True
                        ):
                            open_song_player(song)
                    
                    with col2:
                        safe_s = quote(song)
                        share_url = f"{APP_URL}?song={safe_s}"
                        if responsive_button("🔗 Share", key=f"share_{song}_{idx}", use_container_width=True):
                            st.code(share_url, language="text")
                            st.info("Link copied to clipboard!")
                    
                    with col3:
                        if responsive_button("🗑️ Delete", key=f"delete_{song}_{idx}", use_container_width=True):
                            st.session_state.confirm_delete = song
                            st.rerun()
            
            # Confirmation dialog
            if st.session_state.confirm_delete:
                song_to_delete = st.session_state.confirm_delete
                st.warning(f"⚠️ Are you sure you want to delete **{song_to_delete}**?")
                
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if responsive_button("✅ Yes, Delete", key="confirm_delete", type="primary", use_container_width=True):
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
                    if responsive_button("❌ Cancel", key="cancel_delete", type="secondary", use_container_width=True):
                        st.session_state.confirm_delete = None
                        st.rerun()

    # ================= RESPONSIVE SHARE LINKS =================
    elif page_sidebar == "🔗 Share Links":
        st.subheader("🔗 Manage Shared Links")

        all_songs = get_song_files_cached()
        
        search_query = responsive_text_input(
            "🔍 Search songs...",
            placeholder="Type song name to search",
            key="share_search",
            value=st.session_state.get("search_query", "")
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
                safe_song = quote(song)
                is_shared = song in shared_links_data
                
                if st.session_state.get('mobile_mode', False):
                    # Mobile layout
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        status = "✅ SHARED" if is_shared else "❌ NOT SHARED"
                        st.markdown(f"**{song}** - {status}")
                    
                    with col2:
                        if is_shared:
                            if responsive_button("🚫 Unshare", key=f"unshare_{song}", use_container_width=True):
                                delete_shared_link(song)
                                get_shared_links_cached.clear()
                                st.success(f"✅ {song} unshared!")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            if responsive_button("🔗 Share", key=f"share_{song}", use_container_width=True):
                                save_shared_link(
                                    song,
                                    {"shared_by": st.session_state.user, "active": True}
                                )
                                get_shared_links_cached.clear()
                                share_url = f"{APP_URL}?song={safe_song}"
                                st.success(f"✅ {song} shared!")
                                st.code(share_url, language="text")
                                time.sleep(0.5)
                                st.rerun()
                else:
                    # Desktop layout
                    col1, col2, col3 = st.columns([3, 1, 2])
                    
                    with col1:
                        status = "✅ SHARED" if is_shared else "❌ NOT SHARED"
                        st.write(f"**{song}** - {status}")
                    
                    with col2:
                        if is_shared:
                            if responsive_button("🚫 Unshare", key=f"unshare_{song}", use_container_width=True):
                                delete_shared_link(song)
                                get_shared_links_cached.clear()
                                st.success(f"✅ {song} unshared!")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            if responsive_button("🔗 Share", key=f"share_{song}", use_container_width=True):
                                save_shared_link(
                                    song,
                                    {"shared_by": st.session_state.user, "active": True}
                                )
                                get_shared_links_cached.clear()
                                share_url = f"{APP_URL}?song={safe_song}"
                                st.success(f"✅ {song} shared!")
                                st.code(share_url, language="text")
                                time.sleep(0.5)
                                st.rerun()
                    
                    with col3:
                        if is_shared:
                            share_url = f"{APP_URL}?song={safe_song}"
                            st.markdown(f"""
                            <div style="padding: 5px; background: #f0f0f0; border-radius: 5px; font-size: 12px; word-break: break-all;">
                            🔗 {share_url}
                            </div>
                            """, unsafe_allow_html=True)

# =============== RESPONSIVE USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    save_session_to_db()
    
    st.title(f"🎵 User Dashboard")
    st.markdown(f"*Welcome, {st.session_state.user}*")
    
    # Responsive sidebar
    with st.sidebar:
        st.markdown("### 🎵 Quick Actions")
        
        if responsive_button("🔄 Refresh Songs", key="user_refresh", use_container_width=True):
            get_song_files_cached.clear()
            get_shared_links_cached.clear()
            st.rerun()
            
        if responsive_button("🚪 Logout", key="user_logout", type="secondary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()
    
    st.subheader("🎵 Available Songs")
    
    # Responsive search
    search_query = responsive_text_input(
        "🔍 Search songs...",
        placeholder="Type song name to search",
        key="user_search",
        value=st.session_state.get("search_query", "")
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
        # Responsive song grid
        if st.session_state.get('mobile_mode', False):
            # Mobile - single column
            for idx, song in enumerate(uploaded_songs):
                duration = get_song_duration(song)
                duration_text = f" [{int(duration//60)}:{int(duration%60):02d}]"
                
                if responsive_button(
                    f"🎵 {song}{duration_text}",
                    key=f"user_song_{song}_{idx}",
                    type="primary",
                    use_container_width=True
                ):
                    open_song_player(song)
        else:
            # Desktop - grid layout
            cols_per_row = 3
            for i in range(0, len(uploaded_songs), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    idx = i + j
                    if idx < len(uploaded_songs):
                        song = uploaded_songs[idx]
                        duration = get_song_duration(song)
                        duration_text = f" [{int(duration//60)}:{int(duration%60):02d}]"
                        
                        with cols[j]:
                            if responsive_button(
                                f"🎵 {song}{duration_text}",
                                key=f"user_song_{song}_{idx}",
                                type="secondary",
                                use_container_width=True
                            ):
                                open_song_player(song)

# =============== RESPONSIVE SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    save_session_to_db()
    
    # Responsive song player CSS
    st.markdown("""
    <style>
    /* Song player specific responsive styles */
    .song-player-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: rgba(0,0,0,0.9);
        padding: 10px 15px;
        z-index: 1000;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    @media (max-width: 768px) {
        .song-player-header {
            padding: 8px 10px;
        }
    }
    
    .song-title {
        color: white;
        font-size: 1.2rem;
        margin: 0;
    }
    
    @media (max-width: 480px) {
        .song-title {
            font-size: 1rem;
            max-width: 70%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    selected_song = st.session_state.get("selected_song", None)
    if not selected_song:
        st.error("No song selected!")
        if st.button("Go Back"):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            elif st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            save_session_to_db()
            st.rerun()
        st.stop()
    
    # Check permissions
    shared_links = get_shared_links_cached()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"
    came_from_dashboard = st.session_state.role in ["admin", "user"]
    
    if not (is_admin or came_from_dashboard or is_shared):
        st.error("❌ Access denied!")
        st.stop()
    
    # Responsive header with back button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"<h2 class='song-title'>🎤 {selected_song}</h2>", unsafe_allow_html=True)
    with col2:
        if responsive_button("← Back", key="back_button", type="secondary", use_container_width=True):
            if st.session_state.role == "admin":
                st.session_state.page = "Admin Dashboard"
            elif st.session_state.role == "user":
                st.session_state.page = "User Dashboard"
            st.session_state.selected_song = None
            
            if "song" in st.query_params:
                del st.query_params["song"]
            
            save_session_to_db()
            st.rerun()
    
    # File paths
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
    
    # Get accurate duration
    song_duration = get_song_duration(selected_song)
    
    # Responsive karaoke player template
    karaoke_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>🎤 Sing Along - Karaoke Player</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }
        
        html, body {
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: #000;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            touch-action: manipulation;
        }
        
        #player-container {
            width: 100vw;
            height: 100vh;
            position: relative;
            background: #000;
        }
        
        #lyrics-image {
            width: 100%;
            height: 100%;
            object-fit: contain;
            background: #000;
        }
        
        .controls {
            position: absolute;
            bottom: 20px;
            left: 0;
            right: 0;
            display: flex;
            justify-content: center;
            gap: 10px;
            padding: 0 15px;
            z-index: 100;
        }
        
        .control-btn {
            padding: 12px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            min-width: 120px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
        }
        
        .control-btn:active {
            transform: scale(0.95);
            opacity: 0.8;
        }
        
        .control-btn:hover {
            box-shadow: 0 6px 20px rgba(0,0,0,0.4);
        }
        
        .song-info {
            position: absolute;
            top: 20px;
            left: 20px;
            color: white;
            background: rgba(0,0,0,0.7);
            padding: 10px 15px;
            border-radius: 10px;
            z-index: 100;
            max-width: 80%;
        }
        
        .song-name {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .status {
            font-size: 14px;
            color: #ddd;
        }
        
        /* Mobile optimizations */
        @media (max-width: 768px) {
            .controls {
                bottom: 15px;
                gap: 8px;
                padding: 0 10px;
            }
            
            .control-btn {
                padding: 10px 16px;
                font-size: 13px;
                min-width: 100px;
            }
            
            .song-info {
                top: 15px;
                left: 15px;
                padding: 8px 12px;
            }
            
            .song-name {
                font-size: 14px;
            }
            
            .status {
                font-size: 12px;
            }
        }
        
        @media (max-width: 480px) {
            .controls {
                bottom: 10px;
                gap: 5px;
                padding: 0 8px;
            }
            
            .control-btn {
                padding: 8px 12px;
                font-size: 12px;
                min-width: 90px;
                border-radius: 20px;
            }
            
            .song-info {
                top: 10px;
                left: 10px;
                padding: 6px 10px;
            }
        }
        
        /* 9:16 aspect ratio optimization */
        @media (max-aspect-ratio: 9/16) {
            #lyrics-image {
                object-fit: cover;
                object-position: center top;
            }
            
            .controls {
                flex-direction: column;
                align-items: center;
                bottom: 10px;
            }
            
            .control-btn {
                width: 90%;
                max-width: 200px;
            }
            
            .song-info {
                width: 90%;
                max-width: none;
            }
        }
        
        /* Landscape mode */
        @media (orientation: landscape) and (max-height: 600px) {
            .controls {
                bottom: 5px;
                gap: 5px;
            }
            
            .control-btn {
                padding: 6px 10px;
                font-size: 11px;
                min-width: 80px;
            }
            
            .song-info {
                top: 5px;
                left: 5px;
                padding: 5px 8px;
            }
        }
        
        /* Loading spinner */
        .spinner {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 40px;
            height: 40px;
            border: 4px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #667eea;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: translate(-50%, -50%) rotate(360deg); }
        }
        
        /* Hide elements */
        .hidden {
            display: none !important;
        }
    </style>
</head>
<body>
    <div id="player-container">
        <img id="lyrics-image" src="data:image/jpeg;base64,%%LYRICS_B64%%" 
             alt="Lyrics" onerror="this.style.display='none'">
        
        <div class="song-info">
            <div class="song-name">%%SONG_NAME%%</div>
            <div id="status" class="status">Ready to play 🎤</div>
        </div>
        
        <div class="controls">
            <button id="playBtn" class="control-btn">▶ Play Original</button>
            <button id="recordBtn" class="control-btn">🎙 Start Recording</button>
            <button id="stopBtn" class="control-btn hidden">⏹ Stop Recording</button>
        </div>
        
        <div id="loading" class="spinner hidden"></div>
        
        <!-- Audio elements -->
        <audio id="originalAudio" preload="auto">
            <source src="data:audio/mp3;base64,%%ORIGINAL_B64%%" type="audio/mp3">
        </audio>
        <audio id="accompanimentAudio" preload="auto">
            <source src="data:audio/mp3;base64,%%ACCOMP_B64%%" type="audio/mp3">
        </audio>
    </div>
    
    <script>
        // Elements
        const playerContainer = document.getElementById('player-container');
        const lyricsImage = document.getElementById('lyrics-image');
        const statusEl = document.getElementById('status');
        const playBtn = document.getElementById('playBtn');
        const recordBtn = document.getElementById('recordBtn');
        const stopBtn = document.getElementById('stopBtn');
        const originalAudio = document.getElementById('originalAudio');
        const accompanimentAudio = document.getElementById('accompanimentAudio');
        const loadingSpinner = document.getElementById('loading');
        
        // State
        let isRecording = false;
        let isPlaying = false;
        let mediaRecorder = null;
        let recordedChunks = [];
        
        // Mobile detection
        const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
        const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
        
        // Initialize
        function init() {
            console.log('Karaoke Player Initialized - Mobile:', isMobile);
            
            // Set audio volume
            originalAudio.volume = 1.0;
            accompanimentAudio.volume = 0.25;
            
            // Handle audio errors
            originalAudio.onerror = () => {
                statusEl.textContent = 'Error loading audio';
                showError('Failed to load audio file');
            };
            
            accompanimentAudio.onerror = () => {
                statusEl.textContent = 'Error loading accompaniment';
                showError('Failed to load accompaniment');
            };
            
            // Handle image errors
            lyricsImage.onerror = () => {
                lyricsImage.style.display = 'none';
                playerContainer.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            };
            
            // Preload audio
            setTimeout(() => {
                originalAudio.load();
                accompanimentAudio.load();
                statusEl.textContent = 'Ready 🎤';
            }, 500);
            
            // Add touch feedback
            document.querySelectorAll('.control-btn').forEach(btn => {
                btn.addEventListener('touchstart', function() {
                    this.style.opacity = '0.8';
                });
                
                btn.addEventListener('touchend', function() {
                    this.style.opacity = '1';
                });
            });
        }
        
        // Play original song
        playBtn.addEventListener('click', async () => {
            try {
                if (isPlaying) {
                    originalAudio.pause();
                    originalAudio.currentTime = 0;
                    playBtn.textContent = '▶ Play Original';
                    statusEl.textContent = 'Stopped';
                    isPlaying = false;
                } else {
                    // Stop any recording
                    if (isRecording) {
                        stopRecording();
                    }
                    
                    // Play audio
                    await originalAudio.play();
                    playBtn.textContent = '⏹ Stop';
                    statusEl.textContent = 'Playing original song...';
                    isPlaying = true;
                    
                    // Handle end
                    originalAudio.onended = () => {
                        playBtn.textContent = '▶ Play Original';
                        statusEl.textContent = 'Song finished';
                        isPlaying = false;
                        setTimeout(() => {
                            if (!isRecording && !isPlaying) {
                                statusEl.textContent = 'Ready 🎤';
                            }
                        }, 2000);
                    };
                }
            } catch (error) {
                console.error('Play error:', error);
                statusEl.textContent = 'Playback failed';
                showError('Could not play audio: ' + error.message);
            }
        });
        
        // Start recording
        recordBtn.addEventListener('click', async () => {
            if (isRecording) return;
            
            try {
                showLoading();
                statusEl.textContent = 'Starting recording...';
                
                // Request microphone permission
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        channelCount: 1
                    }
                });
                
                // Start playing accompaniment
                accompanimentAudio.currentTime = 0;
                await accompanimentAudio.play();
                
                // Create media recorder
                mediaRecorder = new MediaRecorder(stream);
                recordedChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        recordedChunks.push(event.data);
                    }
                };
                
                mediaRecorder.onstop = () => {
                    const blob = new Blob(recordedChunks, { type: 'audio/webm' });
                    const url = URL.createObjectURL(blob);
                    
                    // Create download link
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = '%%SONG_NAME%%_recording.webm';
                    a.click();
                    
                    URL.revokeObjectURL(url);
                    statusEl.textContent = 'Recording saved!';
                };
                
                // Start recording
                mediaRecorder.start();
                isRecording = true;
                
                // Update UI
                recordBtn.classList.add('hidden');
                stopBtn.classList.remove('hidden');
                statusEl.textContent = 'Recording... 🎤';
                
                // Auto-stop after song duration
                const duration = %%SONG_DURATION%% * 1000; // Convert to milliseconds
                setTimeout(() => {
                    if (isRecording) {
                        stopRecording();
                    }
                }, duration + 1000);
                
                hideLoading();
                
            } catch (error) {
                console.error('Recording error:', error);
                hideLoading();
                statusEl.textContent = 'Recording failed';
                showError('Microphone access required: ' + error.message);
            }
        });
        
        // Stop recording
        stopBtn.addEventListener('click', () => {
            stopRecording();
        });
        
        // Stop recording function
        function stopRecording() {
            if (!isRecording || !mediaRecorder) return;
            
            mediaRecorder.stop();
            isRecording = false;
            
            // Stop audio
            accompanimentAudio.pause();
            accompanimentAudio.currentTime = 0;
            
            // Update UI
            recordBtn.classList.remove('hidden');
            stopBtn.classList.add('hidden');
            statusEl.textContent = 'Recording stopped';
            
            // Stop all tracks
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
        
        // Show loading
        function showLoading() {
            loadingSpinner.classList.remove('hidden');
        }
        
        // Hide loading
        function hideLoading() {
            loadingSpinner.classList.add('hidden');
        }
        
        // Show error
        function showError(message) {
            alert('Error: ' + message);
        }
        
        // Handle visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Pause audio when tab is hidden
                if (isPlaying) {
                    originalAudio.pause();
                }
                if (isRecording) {
                    stopRecording();
                }
            }
        });
        
        // Handle page unload
        window.addEventListener('beforeunload', () => {
            if (isRecording) {
                stopRecording();
            }
        });
        
        // iOS specific fixes
        if (isIOS) {
            // iOS requires user gesture for audio
            document.addEventListener('touchstart', () => {
                if (originalAudio.paused) {
                    originalAudio.load();
                }
            }, { once: true });
            
            // Prevent double-tap zoom
            document.addEventListener('touchstart', (e) => {
                if (e.touches.length > 1) {
                    e.preventDefault();
                }
            }, { passive: false });
        }
        
        // Initialize on load
        window.addEventListener('load', init);
    </script>
</body>
</html>
"""
    
    # Replace placeholders in template
    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")
    karaoke_html = karaoke_html.replace("%%SONG_NAME%%", selected_song)
    karaoke_html = karaoke_html.replace("%%SONG_DURATION%%", str(song_duration))
    
    # Display the responsive karaoke player
    # Adjust height based on mobile mode
    player_height = 600 if st.session_state.get('mobile_mode', False) else 700
    
    # Use iframe for better isolation
    html(karaoke_html, height=player_height, scrolling=False)

# =============== FALLBACK ===============
else:
    if "song" in st.query_params:
        st.session_state.page = "Song Player"
    else:
        st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()
