import streamlit as st
import os
import base64
from streamlit.components.v1 import html

st.set_page_config(page_title="🎤 Karaoke Reels", layout="wide")

# Base directories
base_dir = os.getcwd()
media_dir = os.path.join(base_dir, "media")
songs_dir = os.path.join(media_dir, "songs")
lyrics_dir = os.path.join(media_dir, "lyrics_images")
logo_dir = os.path.join(media_dir, "logo")
os.makedirs(songs_dir, exist_ok=True)
os.makedirs(lyrics_dir, exist_ok=True)
os.makedirs(logo_dir, exist_ok=True)

# Helper to convert file to base64 text
def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# Logo loading or upload
default_logo_path = os.path.join(logo_dir, "branks3_logo.png")
if not os.path.exists(default_logo_path):
    st.warning("Upload a logo (PNG Transparent recommended)")
    logo_upload = st.file_uploader("Upload Logo (PNG)", type=["png"], key="logo")
    if logo_upload:
        with open(default_logo_path, "wb") as f:
            f.write(logo_upload.getbuffer())
        st.experimental_rerun()
logo_b64 = file_to_base64(default_logo_path)

# Initialize page state if not set
if "page" not in st.session_state:
    st.session_state["page"] = "Songs List"

# Utility function to get all uploaded songs
def get_uploaded_songs():
    songs = []
    for f in os.listdir(songs_dir):
        if f.endswith("_original.mp3"):
            songs.append(f.replace("_original.mp3", ""))
    return sorted(songs)

# MAIN PAGES - Sidebar only for main navigation
if st.session_state["page"] in ["Upload Songs", "Songs List"]:
    # Show sidebar only for main pages
    page_sidebar = st.sidebar.radio("Choose Page", ["Upload Songs", "Songs List"])
    # Sync sidebar with session state
    st.session_state["page"] = page_sidebar

# Upload Songs page
if st.session_state["page"] == "Upload Songs":
    st.title("🎤 Karaoke Reels - Upload Songs")

    st.subheader("Upload New Song")
    col1, col2, col3 = st.columns(3)
    with col1:
        uploaded_original = st.file_uploader("Original Song (_original.mp3)", type=["mp3"], key="original_upload")
    with col2:
        uploaded_accompaniment = st.file_uploader("Accompaniment (_accompaniment.mp3)", type=["mp3"], key="acc_upload")
    with col3:
        uploaded_lyrics_image = st.file_uploader("Lyrics Image (_lyrics_bg.jpg/png)", type=["jpg", "jpeg", "png"], key="lyrics_upload")

    if uploaded_original and uploaded_accompaniment and uploaded_lyrics_image:
        song_name = uploaded_original.name.replace("_original.mp3", "")
        with open(os.path.join(songs_dir, f"{song_name}_original.mp3"), "wb") as f:
            f.write(uploaded_original.getbuffer())
        with open(os.path.join(songs_dir, f"{song_name}_accompaniment.mp3"), "wb") as f:
            f.write(uploaded_accompaniment.getbuffer())
        ext = os.path.splitext(uploaded_lyrics_image.name)[1]
        with open(os.path.join(lyrics_dir, f"{song_name}_lyrics_bg{ext}"), "wb") as f:
            f.write(uploaded_lyrics_image.getbuffer())
        st.success(f"✅ Uploaded: {song_name}")
        st.rerun()

# Songs List page
elif st.session_state["page"] == "Songs List":
    st.title("🎤 Karaoke Reels - Song Library")

    uploaded_songs = get_uploaded_songs()
    if not uploaded_songs:
        st.warning("❌ No songs uploaded yet. Please upload first.")
        st.stop()

    st.write("### Songs available:")

    for s in uploaded_songs:
        if st.button(s):
            st.session_state["selected_song"] = s
            st.session_state["page"] = "Song Player"
            st.rerun()

# Song Player page - PURE FULLSCREEN, NO SCROLL
elif st.session_state["page"] == "Song Player":
    # Remove Streamlit padding, header, scrollbar
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none !important;}
            section[data-testid="stAppViewContainer"] {
                padding: 0 !important;
            }
            div.block-container {
                padding: 0 !important;
                margin: 0 !important;
            }
            header {visibility: hidden !important;}
            /* Hide Streamlit scrollbar */
            ::-webkit-scrollbar {width: 0px; background: transparent;}
            html, body {
                overflow: hidden !important;
            }
        </style>
    """, unsafe_allow_html=True)

    selected_song = st.session_state.get("selected_song", None)
    if not selected_song:
        st.error("No song selected!")
        st.stop()

    # Nothing else on this page (no titles) so no extra scroll
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

    karaoke_template = """ 
    <!doctype html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>Karaoke Reels</title>
    <style>
      * { box-sizing: border-box; }
      html, body {
        margin:0;
        padding:0;
        width:100vw;
        height:100vh;
        overflow:hidden;
        background:black;
        font-family: Poppins, Arial, sans-serif;
        color:#ddd;
      }
      .reel-container {
        width:100vw;
        height:100vh;
        position:relative;
        background:#111;
        display:flex;
        align-items:center;
        justify-content:center;
        flex-direction:column;
      }
      .reel-bg {
        max-width:100%;
        max-height:75vh;
        object-fit:contain;
        border-radius:8px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.8);
      }
      .controls {
        position:relative;
        margin-top:18px;
        text-align:center;
        z-index:30;
      }
      button {
        background:linear-gradient(135deg,#ff0066,#ff66cc);
        border:none;
        color:white;
        padding:10px 18px;
        border-radius:25px;
        font-size:15px;
        cursor:pointer;
        margin:6px;
        box-shadow: 0 4px 18px rgba(255,0,128,0.25);
      }
      button:active { transform:scale(.98); }
      #status {
        position:absolute;
        top:18px;
        width:100%;
        text-align:center;
        font-size:15px;
        color:#ccc;
        text-shadow: 1px 1px 6px rgba(0,0,0,0.9);
      }
      #logoImg {
        position:absolute;
        top:16px;
        left:16px;
        width:60px;
        opacity:0.7;
        z-index:40;
      }
      .final-screen {
        display:none;
        position:fixed;
        top:0;
        left:0;
        width:100vw;
        height:100vh;
        background:rgba(0,0,0,0.95);
        justify-content:center;
        align-items:center;
        flex-direction:column;
        z-index:999;
        gap:12px;
      }
      #canvasPreview { display:none; }
      .note { font-size:13px; color:#bbb; margin-top:8px; }
    </style>
    </head>
    <body>

    <div class="reel-container" id="mainScreen">
      <img id="lyricsImg" class="reel-bg" src="data:image/jpeg;base64,%%LYRICS_B64%%" onerror="this.onerror=null; this.src='';">
      <img id="logoImg" src="data:image/png;base64,%%LOGO_B64%%">
      <div id="status">Ready 🎤</div>

      <audio id="originalAudio" src="data:audio/mp3;base64,%%ORIGINAL_B64%%"></audio>
      <audio id="accompaniment" src="data:audio/mp3;base64,%%ACCOMP_B64%%"></audio>

      <div class="controls">
        <button id="playBtn">▶ Play</button>
        <button id="recordBtn">🎙 Record</button>
        <button id="stopBtn" style="display:none;">⏹ Stop</button>
      </div>

      <div class="note">Recording happens in your browser. Play Recording in same page.</div>
    </div>

    <div class="final-screen" id="finalScreen">
      <div style="text-align:center;">
        <img id="finalPreviewImg" class="reel-bg" style="max-height:60vh;">
      </div>
      <div id="statusFinal" style="color:white;font-size:18px;">Done 🎧</div>
      <div style="display:flex; gap:10px; align-items:center; margin-top:8px;">
        <button id="playRecordingBtn">▶ Play Recording</button>
        <a id="downloadRecordingBtn" download="karaoke_output.webm"><button>⬇ Download (webm)</button></a>
        <button id="newBtn">🔄 Create New</button>
      </div>
      <div class="note">Tip: Recording playback stays on the same page.</div>
    </div>

    <canvas id="canvasPreview"></canvas>

    <script>
    let mediaRecorder;
    let recordedChunks = [];
    let mixedBlob = null;
    let playRecordingAudio = null;
    let isPlaying = false;

    const original = document.getElementById('originalAudio');
    const acc = document.getElementById('accompaniment');

    const status = document.getElementById('status');
    const statusFinal = document.getElementById('statusFinal');

    const playBtn = document.getElementById('playBtn');
    const recordBtn = document.getElementById('recordBtn');
    const stopBtn = document.getElementById('stopBtn');

    const mainScreen = document.getElementById('mainScreen');
    const finalScreen = document.getElementById('finalScreen');
    const playRecordingBtn = document.getElementById('playRecordingBtn');
    const downloadRecordingBtn = document.getElementById('downloadRecordingBtn');
    const newBtn = document.getElementById('newBtn');

    const lyricsImg = document.getElementById('lyricsImg');
    const finalPreviewImg = document.getElementById('finalPreviewImg');

    const canvas = document.getElementById('canvasPreview');
    const ctx = canvas.getContext('2d');

    const logoImg = new Image();
    logoImg.src = "data:image/png;base64,%%LOGO_B64%%";

    async function safePlay(a){try{await a.play();}catch(e){console.log('play blocked',e);} }

    playBtn.onclick = async () => {
        if(original.paused){
            await safePlay(original);
            playBtn.innerText = "⏸ Pause";
            status.innerText="🎵 Playing Song...";
        }else{
            original.pause();
            playBtn.innerText = "▶ Play";
            status.innerText="⏸ Paused";
        }
    };

    recordBtn.onclick = async () => {
        recordedChunks = [];
        status.innerText="🎙 Preparing mic...";
        let micStream;
        try {
            micStream = await navigator.mediaDevices.getUserMedia({
                audio:{ echoCancellation:true, noiseSuppression:true },
                video:false
            });
        } catch(err){
            alert('Allow microphone access');
            return;
        }

        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const micSource = audioCtx.createMediaStreamSource(micStream);

        const accResp = await fetch(acc.src);
        const accBuf = await accResp.arrayBuffer();
        const accDecoded = await audioCtx.decodeAudioData(accBuf);

        const accSource = audioCtx.createBufferSource();
        accSource.buffer = accDecoded;

        const dest = audioCtx.createMediaStreamDestination();
        const micGain = audioCtx.createGain(); micGain.gain.value=1.0;
        const accGain = audioCtx.createGain(); accGain.gain.value=0.7;

        micSource.connect(micGain).connect(dest);
        accSource.connect(accGain).connect(dest);

        const accOutSource = audioCtx.createBufferSource();
        accOutSource.buffer = accDecoded;
        accOutSource.connect(audioCtx.destination);

        accSource.start(); accOutSource.start();
        await new Promise(res=>setTimeout(res,150));

        const img = lyricsImg;
        const w = img.naturalWidth||1280;
        const h = img.naturalHeight||720;
        canvas.width=w; canvas.height=h;
        let rafId;

        function drawFrame(){
            ctx.fillStyle='#000';
            ctx.fillRect(0,0,canvas.width,canvas.height);
            if(img && img.src){
                const iw=img.naturalWidth||canvas.width;
                const ih=img.naturalHeight||canvas.height;
                const scale=Math.max(canvas.width/iw,canvas.height/ih);
                const dw=iw*scale;
                const dh=ih*scale;
                const dx=(canvas.width-dw)/2;
                const dy=(canvas.height-dh)/2;
                ctx.drawImage(img,dx,dy,dw,dh);
            }
            if(logoImg.complete){
                const logoWidth = 100;
                const logoHeight = logoImg.naturalHeight * (logoWidth / logoImg.naturalWidth);
                ctx.globalAlpha = 0.7;
                ctx.drawImage(logoImg, 20, 20, logoWidth, logoHeight);
                ctx.globalAlpha = 1.0;
            }
            rafId=requestAnimationFrame(drawFrame);
        }
        drawFrame();

        const canvasStream = canvas.captureStream(25);
        const mixedAudioStream = dest.stream;
        const combinedStream = new MediaStream();
        canvasStream.getVideoTracks().forEach(t => combinedStream.addTrack(t));
        mixedAudioStream.getAudioTracks().forEach(t => combinedStream.addTrack(t));

        try{
            mediaRecorder = new MediaRecorder(combinedStream, {
                mimeType:'video/webm;codecs=vp8,opus'
            });
        }catch(e){
            mediaRecorder = new MediaRecorder(combinedStream);
        }

        mediaRecorder.ondataavailable = (e) => {
            if(e.data && e.data.size > 0) recordedChunks.push(e.data);
        };
        mediaRecorder.start();

        original.currentTime=0; acc.currentTime=0;
        try{ await original.play(); }catch(e){}
        try{ await acc.play(); }catch(e){}

        playBtn.style.display = "none";
        recordBtn.style.display = "none";
        stopBtn.style.display = "inline-block";
        status.innerText = "🎙 Recording...";

        original.onended = async () => { stopRecording(); };
        stopBtn.onclick = async () => { stopRecording(); };

        async function stopRecording(){
            try{ mediaRecorder.stop(); }catch(e){}
            try{ accSource.stop(); accOutSource.stop(); audioCtx.close(); }catch(e){}
            cancelAnimationFrame(rafId);
            try{ original.pause(); acc.pause(); }catch(e){}
            try{ micStream.getTracks().forEach(t=>t.stop()); }catch(e){}

            status.innerText="⏳ Processing mix... Please wait";
            stopBtn.style.display = "none";

            mediaRecorder.onstop = async () => {
                mixedBlob = new Blob(recordedChunks, { type:'video/webm' });
                const url = URL.createObjectURL(mixedBlob);

                finalPreviewImg.src = lyricsImg.src;
                downloadRecordingBtn.href = url;
                downloadRecordingBtn.setAttribute('download', `${Date.now()}_karaoke_output.webm`);

                mainScreen.style.display = 'none';
                finalScreen.style.display = 'flex';
                statusFinal.innerText = '🎧 Ready';

                playRecordingBtn.onclick = () => {
                    if (!mixedBlob) return;
                    if (!isPlaying) {
                        playRecordingAudio = new Audio(url);
                        playRecordingAudio.play();
                        isPlaying = true;
                        playRecordingBtn.innerText = "⏹ Stop";
                        playRecordingAudio.onended = () => {
                            isPlaying = false;
                            playRecordingBtn.innerText = "▶ Play Recording";
                        };
                    } else {
                        playRecordingAudio.pause();
                        playRecordingAudio.currentTime = 0;
                        isPlaying = false;
                        playRecordingBtn.innerText = "▶ Play Recording";
                    }
                };

                newBtn.onclick = () => {
                    finalScreen.style.display = 'none';
                    mainScreen.style.display = 'flex';
                    status.innerText = "Ready 🎤";
                    playBtn.style.display = "inline-block";
                    playBtn.innerText = "▶ Play";
                    recordBtn.style.display = "inline-block";
                    stopBtn.style.display = "none";
                    if(playRecordingAudio){
                        playRecordingAudio.pause();
                        playRecordingAudio = null;
                        isPlaying = false;
                    }
                    mixedBlob = null;
                    recordedChunks = [];
                };
            };
        }
    };
    </script>

    </body>
    </html>
    """

    karaoke_html = karaoke_template.replace("%%LYRICS_B64%%", lyrics_b64 or "")
    karaoke_html = karaoke_html.replace("%%LOGO_B64%%", logo_b64 or "")
    karaoke_html = karaoke_html.replace("%%ORIGINAL_B64%%", original_b64 or "")
    karaoke_html = karaoke_html.replace("%%ACCOMP_B64%%", accompaniment_b64 or "")

    # Fullscreen karaoke player inside Streamlit – no scroll
    # height taken as full viewport approx (adjust if needed)
    html(karaoke_html, height=700, width=1920)
