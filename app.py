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
import shutil
from PIL import Image
import requests
from io import BytesIO

# =============== LOGO DOWNLOAD AND LOADING ===============
def ensure_logo_exists():
    """Ensure logo exists locally, download from GitHub if not"""
    logo_dir = os.path.join(os.getcwd(), "media", "logo")
    os.makedirs(logo_dir, exist_ok=True)
    
    logo_path = os.path.join(logo_dir, "logoo.png")
    
    # If logo doesn't exist locally, try to download from GitHub
    if not os.path.exists(logo_path):
        try:
            logo_url = "https://github.com/Swarna-0/karaoke_songs-/raw/main/media/logo/logoo.png"
            response = requests.get(logo_url, timeout=10)
            if response.status_code == 200:
                with open(logo_path, "wb") as f:
                    f.write(response.content)
                print(f"✅ Logo downloaded from GitHub")
            else:
                # Create a simple placeholder logo
                img = Image.new('RGB', (512, 512), color='#1E3A8A')
                d = ImageDraw.Draw(img)
                d.text((200, 220), "🎤", fill='white', font_size=100)
                img.save(logo_path, 'PNG')
                print(f"✅ Created placeholder logo")
        except Exception as e:
            print(f"⚠️ Could not download logo: {e}")
            # Create a minimal placeholder
            with open(logo_path, 'wb') as f:
                f.write(b'')
    
    return logo_path

# Try to load logo for page icon
try:
    logo_path = ensure_logo_exists()
    page_icon = Image.open(logo_path)
except:
    page_icon = "𝄞"  # Fallback to emoji if logo fails

# Set page config with logo as icon
st.set_page_config(
    page_title=" Sing Along",
    page_icon=page_icon,
    layout="wide"
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

# =============== CACHED FUNCTIONS FOR PERFORMANCE ===============
@st.cache_data(ttl=5)  # Cache for 5 seconds
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
                      timestamp REAL)''')
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

def save_metadata_to_db(song_name, uploaded_by):
    """Save metadata to database"""
    try:
        conn = sqlite3.connect(session_db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO metadata 
                     (song_name, uploaded_by, timestamp)
                     VALUES (?, ?, ?)''',
                  (song_name, uploaded_by, time.time()))
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
        c.execute('SELECT song_name, uploaded_by FROM metadata')
        results = c.fetchall()
        conn.close()
        
        for song_name, uploaded_by in results:
            metadata[song_name] = {"uploaded_by": uploaded_by, "timestamp": str(time.time())}
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
    
    # Merge with database metadata
    db_metadata = load_metadata_from_db()
    file_metadata.update(db_metadata)
    return file_metadata

def save_metadata(data):
    """Save metadata to both file and database"""
    # Save to file
    with open(metadata_path, "w") as f:
        json.dump(data, f, indent=2)
    
    # Save to database
    for song_name, info in data.items():
        uploaded_by = info.get("uploaded_by", "unknown")
        save_metadata_to_db(song_name, uploaded_by)

def delete_metadata(song_name):
    """Delete metadata from both file and database"""
    # Load existing metadata
    metadata = load_metadata()
    
    # Remove from metadata
    if song_name in metadata:
        del metadata[song_name]
    
    # Save updated metadata to file
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Delete from database
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
    
    # Merge with database links
    db_links = load_shared_links_from_db()
    file_links.update(db_links)
    return file_links

def save_shared_link(song_name, link_data):
    """Save shared link to both file and database"""
    # Save to file
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    with open(filepath, 'w') as f:
        json.dump(link_data, f)
    
    # Save to database
    shared_by = link_data.get("shared_by", "unknown")
    save_shared_link_to_db(song_name, shared_by)

def delete_shared_link(song_name):
    """Delete shared link from both file and database"""
    # Delete from file
    filepath = os.path.join(shared_links_dir, f"{song_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete from database
    delete_shared_link_from_db(song_name)

def get_uploaded_songs(show_unshared=False):
    """Get list of uploaded songs"""
    return get_song_files_cached()

def delete_song_files(song_name):
    """Delete all files related to a song"""
    try:
        # Delete original song file
        original_path = os.path.join(songs_dir, f"{song_name}_original.mp3")
        if os.path.exists(original_path):
            os.remove(original_path)
        
        # Delete accompaniment file
        acc_path = os.path.join(songs_dir, f"{song_name}_accompaniment.mp3")
        if os.path.exists(acc_path):
            os.remove(acc_path)
        
        # Delete lyrics image files
        for ext in [".jpg", ".jpeg", ".png"]:
            lyrics_path = os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{ext}")
            if os.path.exists(lyrics_path):
                os.remove(lyrics_path)
        
        # Delete shared link file
        shared_link_path = os.path.join(shared_links_dir, f"{song_name}.json")
        if os.path.exists(shared_link_path):
            os.remove(shared_link_path)
        
        # Clear cache
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

        # Always set song from URL
        st.session_state.selected_song = song_from_url
        st.session_state.page = "Song Player"

        # Auto guest if not logged in
        if not st.session_state.get("user"):
            st.session_state.user = "guest"
            st.session_state.role = "guest"

        save_session_to_db()


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
    # Don't show uploader on login page to avoid rerun issues
    pass
logo_b64 = file_to_base64(default_logo_path) if os.path.exists(default_logo_path) else ""

# =============== RESPONSIVE LOGIN PAGE (NO SCROLLING) ===============
if st.session_state.page == "Login":
    # Save session state
    save_session_to_db()
    
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    header {visibility:hidden;}
    
    /* COMPLETELY PREVENT SCROLLING ON LOGIN PAGE */
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
    
    /* FIXED BACKGROUND - NO SCROLLING */
    body {
        background: radial-gradient(circle at top,#335d8c 0,#0b1b30 55%,#020712 100%);
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        overflow: hidden !important;
    }

    /* INNER CONTENT PADDING */
    .login-content {
        padding: 1.8rem 2.2rem 2.2rem 2.2rem;
        max-height: 90vh;
        overflow-y: auto;
    }

    /* CENTERED HEADER SECTION */
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

    /* INPUTS BLEND WITH BOX */
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
    
    /* RESPONSIVE COLUMNS FOR MOBILE */
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
        
        /* MOBILE TEXT SIZE ADJUSTMENTS */
        .stTextInput input {
            font-size: 14px !important;
            padding: 10px 12px !important;
        }
        
        .stButton button {
            font-size: 14px !important;
            height: 40px !important;
        }
    }
    
    /* UPDATED CONTACT LINKS - NO UNDERLINE, ONE ROW WITH ORIGINAL COLORS */
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
    
    /* EMAIL - GOOGLE COLORS */
    .contact-link-item.email {
        color: #4285F4 !important;
        background: rgba(66, 133, 244, 0.1);
        border: none;
    }
    
    /* INSTAGRAM - ORIGINAL GRADIENT */
    .contact-link-item.instagram {
        background: linear-gradient(45deg, #405DE6, #5851DB, #833AB4, #C13584, #E1306C, #FD1D1D) !important;
        -webkit-background-clip: text !important;
        background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        text-fill-color: transparent !important;
        border: none;
    }
    
    /* YOUTUBE - RED COLOR */
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
    
    /* USER/ADMIN DASHBOARD BUTTONS - SAME ROW, SMALLER TEXT FOR MOBILE */
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
    
    @media (max-width: 768px) {
        .dashboard-buttons-row {
            gap: 5px;
        }
        
        .dashboard-button {
            font-size: 0.65rem;
            padding: 3px 8px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # -------- CENTER ALIGN COLUMN --------
    left, center, right = st.columns([1, 1.5, 1])

    with center:
        st.markdown('<div class="login-content">', unsafe_allow_html=True)

        # Header with better spacing
        st.markdown(f"""
        <div class="login-header">
            <img src="data:image/png;base64,{logo_b64}">
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
                    st.session_state.selected_song = None  # Clear any song selection
                    save_session_to_db()
                    st.rerun()
                elif username == "branks3" and USER1_HASH and hashed_pass == USER1_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.session_state.selected_song = None  # Clear any song selection
                    save_session_to_db()
                    st.rerun()
                elif username == "user2" and USER2_HASH and hashed_pass == USER2_HASH:
                    st.session_state.user = username
                    st.session_state.role = "user"
                    st.session_state.page = "User Dashboard"
                    st.session_state.selected_song = None  # Clear any song selection
                    save_session_to_db()
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

        # UPDATED CONTACT ADMIN SECTION WITH EMAIL AND INSTAGRAM OPTIONS
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

        st.markdown('</div></div>', unsafe_allow_html=True)

# =============== ADMIN DASHBOARD ===============
elif st.session_state.page == "Admin Dashboard" and st.session_state.role == "admin":
    # Auto-save session
    save_session_to_db()
    
    # Add mobile-responsive styles for admin dashboard
    st.markdown("""
    <style>
    /* ADMIN DASHBOARD MOBILE STYLES */
    @media (max-width: 768px) {
        /* Reduce title size */
        h1 {
            font-size: 1.5rem !important;
        }
        
        /* Reduce subheader size */
        h3 {
            font-size: 1.2rem !important;
        }
        
        /* Reduce button text size */
        .stButton > button {
            font-size: 14px !important;
            padding: 8px 12px !important;
        }
        
        /* Reduce radio button text */
        .stRadio > div[role="radiogroup"] > label {
            font-size: 14px !important;
        }
        
        /* Reduce sidebar text */
        [data-testid="stSidebar"] * {
            font-size: 14px !important;
        }
        
        /* Adjust song list items */
        .song-name {
            font-size: 14px !important;
        }
        
        /* Adjust columns for mobile */
        .stColumn {
            padding: 2px !important;
        }
        
        /* Search bar mobile optimization */
        .stTextInput > div > div > input {
            font-size: 14px !important;
            padding: 8px !important;
        }
    }
    
    /* DELETE BUTTON STYLING - NO BACKGROUND, NO BORDER, NO PADDING */
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
    
    /* SONG LIST ITEMS - CLEAN LAYOUT */
    .song-item-row {
        display: flex;
        align-items: center;
        margin-bottom: 4px !important;
        padding: 0 !important;
        background: transparent !important;
    }
    
    /* PLAY BUTTON STYLING */
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
    
    /* SHARE BUTTON STYLING */
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
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"👑 Admin Dashboard - {st.session_state.user}")

    page_sidebar = st.sidebar.radio(
        "Navigate",
        ["Upload Songs", "Songs List", "Share Links"],
        key="admin_nav"
    )

    # ================= UPLOAD SONGS =================
    if page_sidebar == "Upload Songs":
        st.subheader("📤 Upload New Song")

        # ✅ SONG NAME INPUT
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
                type=["jpg", "jpeg", "png"],
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

                metadata = get_metadata_cached()
                metadata[song_name] = {
                    "uploaded_by": st.session_state.user,
                    "timestamp": str(time.time())
                }
                save_metadata(metadata)

                # Clear cache
                get_song_files_cached.clear()
                get_metadata_cached.clear()

                st.success(f"✅ Song Uploaded Successfully: {song_name}")
                st.balloons()
                time.sleep(1)
                st.rerun()

    # ================= SONGS LIST =================
    elif page_sidebar == "Songs List":
        st.subheader("🎵 All Songs List (Admin View)")
        
        # SEARCH BAR WITH PLACEHOLDER
        search_query = st.text_input(
            "🔍 Search songs...",
            value=st.session_state.get("search_query", ""),
            placeholder="Type song name to search",
            key="admin_search"
        )
        st.session_state.search_query = search_query
        
        uploaded_songs = get_song_files_cached()
        
        # Filter songs based on search query
        if search_query:
            uploaded_songs = [song for song in uploaded_songs 
                            if search_query.lower() in song.lower()]
        
        if not uploaded_songs:
            if search_query:
                st.warning(f"❌ No songs found matching '{search_query}'")
            else:
                st.warning("❌ No songs uploaded yet.")
        else:
            # Clean layout with minimal styling
            for idx, s in enumerate(uploaded_songs):
                # Create columns for each song
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    # Clickable song name - simple text
                    if st.button(
                        f"🎶 {s}",
                        key=f"song_name_{s}_{idx}",
                        help="Click to play song",
                        use_container_width=True,
                        type="secondary"
                    ):
                        open_song_player(s)
                
                with col2:
                    # Share link icon - using button with emoji
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
                    # Delete button - simple trash icon with minimal styling
                    if st.button(
                        "🗑️",
                        key=f"delete_{s}_{idx}",
                        help="Delete song"
                    ):
                        st.session_state.confirm_delete = s
                        st.rerun()
            
            # Confirmation dialog for deletion
            if st.session_state.confirm_delete:
                song_to_delete = st.session_state.confirm_delete
                st.warning(f"⚠️ Are you sure you want to delete **{song_to_delete}**?")
                
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✅ Yes, Delete", type="primary"):
                        # Delete song files
                        if delete_song_files(song_to_delete):
                            # Delete metadata
                            delete_metadata(song_to_delete)
                            # Delete shared link if exists
                            delete_shared_link(song_to_delete)
                            
                            st.success(f"✅ Song '{song_to_delete}' deleted successfully!")
                            st.session_state.confirm_delete = None
                            
                            # Clear all caches
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

    # ================= SHARE LINKS =================
    elif page_sidebar == "Share Links":
        st.header("🔗 Manage Shared Links")

        all_songs = get_song_files_cached()
        
        # SEARCH BAR WITH PLACEHOLDER
        search_query = st.text_input(
            "🔍 Search songs...",
            value=st.session_state.get("search_query", ""),
            placeholder="Type song name to search",
            key="share_search"
        )
        st.session_state.search_query = search_query
        
        # Filter songs based on search query
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
            # Simple display
            for song in all_songs:
                # Create columns for each song
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    safe_song = quote(song)
                    is_shared = song in shared_links_data
                    status = "✅ SHARED" if is_shared else "❌ NOT SHARED"
                    st.write(f"**{song}** - {status}")
                
                with col2:
                    # Create buttons
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

    # ================= LOGOUT =================
    if st.sidebar.button("Logout", key="admin_logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "Login"
        save_session_to_db()
        st.rerun()

# =============== USER DASHBOARD ===============
elif st.session_state.page == "User Dashboard" and st.session_state.role == "user":
    # Auto-save session
    save_session_to_db()
    
    # Add mobile-responsive styles for user dashboard
    st.markdown("""
    <style>
    /* USER DASHBOARD MOBILE STYLES */
    @media (max-width: 768px) {
        /* Reduce title size */
        h3 {
            font-size: 1.2rem !important;
        }
        
        /* Reduce sidebar header */
        [data-testid="stSidebar"] h2 {
            font-size: 1.3rem !important;
        }
        
        /* Reduce sidebar subheader */
        [data-testid="stSidebar"] h3 {
            font-size: 1.1rem !important;
        }
        
        /* Reduce button text size */
        .stButton > button {
            font-size: 14px !important;
            padding: 8px 12px !important;
        }
        
        /* Reduce user song name text */
        .user-song-name {
            font-size: 14px !important;
        }
        
        /* Search bar mobile optimization */
        .stTextInput > div > div > input {
            font-size: 14px !important;
            padding: 8px !important;
        }
    }
    
    /* CLICKABLE SONG NAMES - NO BACKGROUND, NO BORDERS */
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
    </style>
    """, unsafe_allow_html=True)

    # 🔹 SIDEBAR - UPDATED WITH "User Dashboard" TEXT
    with st.sidebar:
        # Display "User Dashboard" title
        st.markdown("<h2 style='text-align: center;'>🎵 User Dashboard</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown("### Quick Actions")
        
        if st.button("🔄 Refresh Songs List", key="user_refresh"):
            # Clear caches for refresh
            get_song_files_cached.clear()
            get_shared_links_cached.clear()
            st.rerun()
            
        if st.button("Logout", key="user_sidebar_logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.page = "Login"
            save_session_to_db()
            st.rerun()

    # 🔹 MAIN CONTENT - UPDATED FOR MOBILE RESPONSIVE DESIGN
    st.subheader("🎵 Available Songs (Only Shared Songs)")
    
    # SEARCH BAR WITH PLACEHOLDER
    search_query = st.text_input(
        "🔍 Search songs...",
        value=st.session_state.get("search_query", ""),
        placeholder="Type song name to search",
        key="user_search"
    )
    st.session_state.search_query = search_query
    
    all_songs = get_song_files_cached()
    shared_links = get_shared_links_cached()
    
    # Filter only shared songs
    uploaded_songs = [song for song in all_songs if song in shared_links]
    
    # Filter songs based on search query
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
        # Simple list display
        for idx, song in enumerate(uploaded_songs):
            # Clickable song name
            if st.button(
                f"✅ *{song}*",
                key=f"user_song_{song}_{idx}",
                help="Click to play song",
                use_container_width=True,
                type="secondary"
            ):
                open_song_player(song)

# =============== SONG PLAYER ===============
elif st.session_state.page == "Song Player" and st.session_state.get("selected_song"):
    # Auto-save session
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
        margin: 0 !important;
        width: 100vw !important;
        max-width: 100vw !important;
        overflow: hidden !important;
    }
    html, body {
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
    }
    #root > div > div > div > div > section > div {padding-top: 0rem !important;}
    .stApp {
        overflow: hidden !important;
        width: 100vw !important;
        height: 100vh !important;
    }
    
    /* MOBILE RESPONSIVE FOR SONG PLAYER BACK BUTTON */
    @media (max-width: 768px) {
        .stButton > button[kind="secondary"] {
            font-size: 14px !important;
            padding: 8px 12px !important;
            margin: 5px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    selected_song = st.session_state.get("selected_song", None)
    if not selected_song:
        st.error("No song selected!")
        # Show back button only for logged-in users
        if st.session_state.role in ["admin", "user"]:
            if st.button("Go Back"):
                if st.session_state.role == "admin":
                    st.session_state.page = "Admin Dashboard"
                elif st.session_state.role == "user":
                    st.session_state.page = "User Dashboard"
                save_session_to_db()
                st.rerun()
        st.stop()

    # Double-check access permission
    shared_links = get_shared_links_cached()
    is_shared = selected_song in shared_links
    is_admin = st.session_state.role == "admin"
    is_guest = st.session_state.role == "guest"

    # Allow if:
    # 1. Admin
    # 2. User already inside app (dashboard nundi vacharu)
    # 3. Guest with shared link
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

    # ✅ UPDATED KARAOKE TEMPLATE WITH MOBILE-FRIENDLY 9:16 DOWNLOAD AND CLEAR LOGO
    karaoke_template = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>🎤 sing_along </title>
<style>
* { 
    margin: 0; 
    padding: 0; 
    box-sizing: border-box; 
}
html, body {
    overflow: hidden !important;
    width: 100vw !important;
    height: 100vh !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    background: #000 !important;
}
body { 
    background: #000; 
    font-family: 'Poppins', sans-serif; 
    height: 100vh !important;
    width: 100vw !important;
    overflow: hidden !important;
    position: fixed !important;
}
.reel-container, .final-reel-container { 
    width: 100vw !important; 
    height: 100vh !important; 
    position: absolute; 
    background: #111; 
    overflow: hidden !important;
}
#status { 
    position: absolute; 
    top: 20px; 
    width: 100%; 
    text-align: center; 
    font-size: 14px; 
    color: #ccc; 
    z-index: 20; 
    text-shadow: 1px 1px 6px rgba(0,0,0,0.9); 
}
.reel-bg { 
    position: absolute; 
    top: 0; 
    left: 0; 
    width: 100vw !important; 
    height: 85vh !important; 
    object-fit: contain !important;
    object-position: top !important;
}
.lyrics { 
    position: absolute; 
    bottom: 25%; 
    width: 100%; 
    text-align: center; 
    font-size: 2vw; 
    font-weight: bold; 
    color: white; 
    text-shadow: 2px 2px 10px black; 
}
.controls { 
    position: absolute; 
    bottom: 20%; 
    width: 100%; 
    text-align: center; 
    z-index: 30; 
}
button { 
    background: linear-gradient(135deg, #ff0066, #ff66cc); 
    border: none; 
    color: white; 
    padding: 8px 20px; 
    border-radius: 25px; 
    font-size: 13px; 
    margin: 4px; 
    box-shadow: 0px 3px 15px rgba(255,0,128,0.4); 
    cursor: pointer; 
}
button:active { 
    transform: scale(0.95); 
}
.final-output { 
    position: fixed !important; 
    width: 100vw !important; 
    height: 100vh !important; 
    top: 0 !important; 
    left: 0 !important; 
    background: rgba(0,0,0,0.9); 
    display: none; 
    justify-content: center; 
    align-items: center; 
    z-index: 999; 
}
#logoImg { 
    position: absolute; 
    top: 20px; 
    left: 20px; 
    width: 40px;
    height: 40px;
    z-index: 50; 
    opacity: 1; /* CHANGED FROM 0.6 TO 1 FOR CLEAR LOGO */
    filter: brightness(1.2); /* MAKE LOGO CLEARER */
}
canvas { 
    display: none; 
}
.back-button { 
    position: absolute; 
    top: 20px; 
    right: 20px; 
    background: rgba(0,0,0,0.7); 
    color: white; 
    padding: 8px 16px; 
    border-radius: 20px; 
    text-decoration: none; 
    font-size: 14px; 
    z-index: 100; 
}
</style>
</head>
<body>

<div class="reel-container" id="reelContainer">
    <img class="reel-bg" id="mainBg" src="data:image/jpeg;base64,%%LYRICS_B64%%">
    <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
    <div id="status">Ready 🎤</div>
    <audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%"></audio>
    <audio id="accompaniment" src="data:audio/mp3;base64,%%ACCOMP_B64%%"></audio>
    <div class="controls">
      <button id="playBtn">▶ Play</button>
      <button id="recordBtn">🎙 Record</button>
      <button id="stopBtn" style="display:none;">⏹ Stop</button>
    </div>
</div>

<div class="final-output" id="finalOutputDiv">
  <div class="final-reel-container">
    <img class="reel-bg" id="finalBg">
    <div id="status"></div>
    <div class="lyrics" id="finalLyrics"></div>
    <div class="controls">
      <button id="playRecordingBtn">▶ Play</button>
      <a id="downloadRecordingBtn" href="#" download>
        <button>⬇ Download</button>
      </a>
      <button id="newRecordingBtn">🔄 New Recording</button>
    </div>
  </div>
</div>

<canvas id="recordingCanvas" width="1080" height="1920"></canvas> <!-- CHANGED TO 9:16 ASPECT RATIO -->

<script>
/* ================== GLOBAL STATE ================== */
let mediaRecorder;
let recordedChunks = [];
let playRecordingAudio = null;
let lastRecordingURL = null;

let audioContext, micSource, accSource;
let canvasRafId = null;
let isRecording = false;
let isPlayingRecording = false;

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

const playRecordingBtn = document.getElementById("playRecordingBtn");
const downloadRecordingBtn = document.getElementById("downloadRecordingBtn");
const newRecordingBtn = document.getElementById("newRecordingBtn");

const canvas = document.getElementById("recordingCanvas");
const ctx = canvas.getContext("2d");

const logoImg = new Image();
logoImg.src = document.getElementById("logoImg").src;

/* ================== AUDIO CONTEXT FIX ================== */
async function ensureAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === "suspended") {
        await audioContext.resume();
    }
}

async function safePlay(audio) {
    try {
        await ensureAudioContext();
        await audio.play();
    } catch (e) {
        console.log("Autoplay blocked:", e);
    }
}

document.addEventListener("visibilitychange", async () => {
    if (!document.hidden) await ensureAudioContext();
});

/* ================== PLAY ORIGINAL ================== */
playBtn.onclick = async () => {
    await ensureAudioContext();
    if (originalAudio.paused) {
        originalAudio.currentTime = 0;
        await safePlay(originalAudio);
        playBtn.innerText = "⏹ Stop";
        status.innerText = "🎵 Playing song...";
    } else {
        originalAudio.pause();
        playBtn.innerText = "▶ Play";
        status.innerText = "⏹ Stopped";
    }
};

/* ================== CANVAS DRAW FOR MOBILE 9:16 ================== */
function drawCanvas() {
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Mobile-friendly 9:16 aspect ratio (1080x1920)
    const canvasW = canvas.width; // 1080
    const canvasH = canvas.height * 0.85; // 1920 * 0.85 = ~1632

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
    const y = 0; // TOP aligned

    ctx.drawImage(mainBg, x, y, drawW, drawH);

    /* LOGO - CLEAR AND VISIBLE */
    ctx.globalAlpha = 1; // FULL VISIBILITY
    ctx.drawImage(logoImg, 100, 100, 100, 100);
    ctx.globalAlpha = 1;

    canvasRafId = requestAnimationFrame(drawCanvas);
}

/* ================== RECORD ================== */
recordBtn.onclick = async () => {
    if (isRecording) return;
    isRecording = true;

    await ensureAudioContext();
    recordedChunks = [];

    /* MIC */
    const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    micSource = audioContext.createMediaStreamSource(micStream);

    /* ACCOMPANIMENT */
    const accRes = await fetch(accompanimentAudio.src);
    const accBuf = await accRes.arrayBuffer();
    const accDecoded = await audioContext.decodeAudioData(accBuf);

    accSource = audioContext.createBufferSource();
    accSource.buffer = accDecoded;

    const destination = audioContext.createMediaStreamDestination();
    micSource.connect(destination);
    accSource.connect(destination);

    accSource.start();

    // Set canvas to 9:16 mobile aspect ratio
    canvas.width = 1080;
    canvas.height = 1920;
    drawCanvas();

    const stream = new MediaStream([
        ...canvas.captureStream(30).getTracks(),
        ...destination.stream.getTracks()
    ]);

    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => e.data.size && recordedChunks.push(e.data);

    mediaRecorder.onstop = () => {
        cancelAnimationFrame(canvasRafId);

        const blob = new Blob(recordedChunks, { type: "video/mp4" }); // CHANGED TO MP4
        const url = URL.createObjectURL(blob);

        if (lastRecordingURL) URL.revokeObjectURL(lastRecordingURL);
        lastRecordingURL = url;

        finalBg.src = mainBg.src;
        finalDiv.style.display = "flex";

        // ✅ DOWNLOAD WITH SONG NAME + .mp4
        const songName = "%%SONG_NAME%%".replace(/[^a-zA-Z0-9]/g, '_');
        const fileName = songName + ".mp4";
        downloadRecordingBtn.href = url;
        downloadRecordingBtn.download = fileName;

        playRecordingBtn.onclick = () => {
            if (!isPlayingRecording) {
                playRecordingAudio = new Audio(url);
                playRecordingAudio.play();
                playRecordingBtn.innerText = "⏹ Stop";
                isPlayingRecording = true;
                playRecordingAudio.onended = resetPlayBtn;
            } else {
                resetPlayBtn();
            }
        };
    };

    mediaRecorder.start();

    originalAudio.currentTime = 0;
    accompanimentAudio.currentTime = 0;
    await safePlay(originalAudio);
    await safePlay(accompanimentAudio);

    playBtn.style.display = "none";
    recordBtn.style.display = "none";
    stopBtn.style.display = "inline-block";
    status.innerText = "🎙 Recording...";
    
    // ✅ AUTOMATIC STOP: Set timeout to stop recording when song ends
    const songDuration = originalAudio.duration * 1000; // Convert to milliseconds
    setTimeout(() => {
        if (isRecording) {
            stopBtn.click(); // Automatically click stop button
        }
    }, songDuration + 500); // Add 500ms buffer
};

/* ================== STOP ================== */
stopBtn.onclick = () => {
    if (!isRecording) return;
    isRecording = false;

    try { mediaRecorder.stop(); } catch {}
    try { accSource.stop(); } catch {}

    originalAudio.pause();
    accompanimentAudio.pause();

    stopBtn.style.display = "none";
    status.innerText = "⏹ Processing...";
};

/* ================== HELPERS ================== */
function resetPlayBtn() {
    if (playRecordingAudio) {
        playRecordingAudio.pause();
        playRecordingAudio.currentTime = 0;
    }
    playRecordingBtn.innerText = "▶ Play";
    isPlayingRecording = false;
}

/* ================== NEW RECORDING ================== */
newRecordingBtn.onclick = () => {
    finalDiv.style.display = "none";

    recordedChunks = [];
    isRecording = false;
    isPlayingRecording = false;

    originalAudio.pause();
    accompanimentAudio.pause();
    originalAudio.currentTime = 0;
    accompanimentAudio.currentTime = 0;

    if (playRecordingAudio) {
        playRecordingAudio.pause();
        playRecordingAudio = null;
    }

    playBtn.style.display = "inline-block";
    recordBtn.style.display = "inline-block";
    stopBtn.style.display = "none";
    playBtn.innerText = "▶ Play";
    status.innerText = "Ready 🎤";
};

/* ================== SONG END DETECTION ================== */
originalAudio.addEventListener('ended', () => {
    if (isRecording) {
        // If recording is still active when song ends, stop it
        setTimeout(() => {
            if (isRecording) {
                stopBtn.click();
            }
        }, 100);
    }
});

accompanimentAudio.addEventListener('ended', () => {
    if (isRecording) {
        // If recording is still active when accompaniment ends, stop it
        setTimeout(() => {
            if (isRecording) {
                stopBtn.click();
            }
        }, 100);
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

    # ✅ BACK BUTTON LOGIC
    if st.session_state.role in ["admin", "user"]:
        col1, col2 = st.columns([5, 1])
        with col2:
            if st.button("← Back to Dashboard", key="back_player"):
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
    else:
        st.empty()

    html(karaoke_html, height=800, width=1920, scrolling=False)

# =============== FALLBACK ===============
else:
    if "song" in st.query_params:
        st.session_state.page = "Song Player"
    else:
        st.session_state.page = "Login"
    save_session_to_db()
    st.rerun()

# =============== DEBUG INFO (Hidden by default) ===============
with st.sidebar:
    if st.session_state.get("role") == "admin":
        if st.checkbox("Show Debug Info", key="debug_toggle"):
            st.write("### Debug Info")
            st.write(f"Page: {st.session_state.get('page')}")
            st.write(f"User: {st.session_state.get('user')}")
            st.write(f"Role: {st.session_state.get('role')}")
            st.write(f"Selected Song: {st.session_state.get('selected_song')}")
            st.write(f"Query Params: {dict(st.query_params)}")
            
            if st.button("Force Reset", key="debug_reset"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.page = "Login"
                save_session_to_db()
                st.rerun()
