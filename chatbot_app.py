# app_gia_su_ao_final_stable.py
import streamlit as st
import requests, base64, uuid, io, time, hashlib, json
from datetime import datetime

# --------------------------
# CONFIG
# --------------------------
API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
if not API_KEY:
    st.error("⚠️ Thiếu GEMINI_API_KEY trong .streamlit/secrets.toml. Vui lòng kiểm tra lại cấu hình.")
    st.stop()

MODEL_OPTIONS = {
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
}

# System instruction - keep concise to save tokens
SYSTEM_INSTRUCTION = (
    "Bạn là gia sư ảo thân thiện cho học sinh cấp 2-3. Trình bày rõ ràng, dùng LaTeX khi cần."
)

STYLE_PROMPT_MAP = {
    "Gia sư trẻ trung": "young friendly tutor, smiling, colorful, modern, cartoon-realistic style"
}

# Soft limits & tuning
API_COOLDOWN_SECONDS = 3       # debounce to prevent spam (per-session)
SESSION_REQUEST_SOFT_LIMIT = 300  # soft request cap per session to avoid runaway usage
HISTORY_KEEP = 4               # keep last N messages in session (for display); when sending, use shorter
HISTORY_TO_SEND = 2            # how many last messages (user+assistant) to include in prompt
CACHE_MAX_ITEMS = 1000         # cache size in memory

st.set_page_config(page_title="Gia Sư Ảo", layout="wide", page_icon="🤖")

# --------------------------
# SESSION INIT (preserve existing data)
# --------------------------
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "image_history" not in st.session_state:
    st.session_state["image_history"] = []
if "chosen_model" not in st.session_state:
    st.session_state["chosen_model"] = MODEL_OPTIONS[list(MODEL_OPTIONS.keys())[0]]

for key in ["user_name", "user_class", "user_input_area", "pending_action", "temp_question", "tts_enabled", "style"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key not in ["tts_enabled"] else False

# New session-level tracking for optimizations
if "api_call_count" not in st.session_state:
    st.session_state["api_call_count"] = 0
if "last_api_call_time" not in st.session_state:
    st.session_state["last_api_call_time"] = 0.0
if "cache_answers" not in st.session_state:
    st.session_state["cache_answers"] = {}  # key -> answer
if "cache_order" not in st.session_state:
    st.session_state["cache_order"] = []  # maintain simple FIFO for eviction

# --------------------------
# HELPERS: cache, throttle, history compress
# --------------------------
def _cache_key_for(prompt, model):
    # normalize prompt -> small hash to use as key
    k = prompt.strip().lower()
    h = hashlib.sha256((model + "|" + k).encode("utf-8")).hexdigest()
    return h

def get_cached_answer(prompt, model):
    key = _cache_key_for(prompt, model)
    return st.session_state["cache_answers"].get(key)

def save_cache(prompt, model, answer):
    key = _cache_key_for(prompt, model)
    if key in st.session_state["cache_answers"]:
        return
    # Evict oldest if above limit
    if len(st.session_state["cache_order"]) >= CACHE_MAX_ITEMS:
        old = st.session_state["cache_order"].pop(0)
        if old in st.session_state["cache_answers"]:
            del st.session_state["cache_answers"][old]
    st.session_state["cache_answers"][key] = answer
    st.session_state["cache_order"].append(key)

def can_call_api():
    """Throttle to prevent spam."""
    now = time.time()
    last = st.session_state.get("last_api_call_time", 0.0)
    if now - last < API_COOLDOWN_SECONDS:
        return False
    st.session_state["last_api_call_time"] = now
    # Enforce soft session cap
    if st.session_state.get("api_call_count", 0) >= SESSION_REQUEST_SOFT_LIMIT:
        return False
    return True

def incr_api_count():
    st.session_state["api_call_count"] = st.session_state.get("api_call_count", 0) + 1

def compress_history_for_api(full_history, max_turns=HISTORY_TO_SEND):
    """
    full_history: list of {"role":..., "text":...}
    We'll send a small context: system + last user message + last assistant message (if exist).
    """
    # find last user and assistant messages
    if not full_history:
        return []
    # take last max_turns messages
    recent = full_history[-max_turns:]
    # Convert to simplified lines
    simplified = []
    for msg in recent:
        role = msg.get("role", "user")
        text = msg.get("text", "")
        # strip heavy markdown or images
        simplified.append({"role": role, "text": text})
    return simplified

# --------------------------
# API CALLS (wrapped & optimized)
# --------------------------
def call_gemini_text(model, user_prompt, short_history=None):
    """
    Optimized API call:
    - Compose prompt with SYSTEM_INSTRUCTION
    - Attach only last few messages (short_history) to reduce token usage
    - Return (text, err)
    """
    # Compose minimal prompt
    user_name = st.session_state.get("user_name", "học sinh")
    user_class = st.session_state.get("user_class", "Chưa rõ")
    personal_context = (
        f"Học sinh: {user_name} (Lớp {user_class}). Trả lời ngắn gọn, thân thiện."
    )

    # Build content to send: minimal
    # We'll include system instruction, personal context, optionally one assistant reply for continuity, then user prompt
    contents_parts = []
    # System instruction as initial system-like text
    contents_parts.append({"role":"system", "text": SYSTEM_INSTRUCTION})
    contents_parts.append({"role":"system", "text": personal_context})

    # include short_history if provided (kept minimal)
    if short_history:
        for m in short_history:
            # include only textual parts and cut to modest length
            t = m.get("text", "")
            if len(t) > 1000:
                t = t[:1000] + "..."
            contents_parts.append({"role": m.get("role", "user"), "text": t})

    # Final user message
    contents_parts.append({"role":"user", "text": user_prompt})

    payload = {"contents": [{"role":"user", "parts": [{"text": json.dumps(contents_parts)}]}]}

    # Note: We wrap the parts as JSON string in one part to ensure minimal overhead, but adjust if your API expects direct
    # Here we follow the minimal approach previously used; if your endpoint requires different format, adapt accordingly.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"

    try:
        res = requests.post(url, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        # defensive extraction
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            # Attempt other extraction patterns
            text = json.dumps(data)
        incr_api_count()
        return text, None
    except requests.exceptions.HTTPError as http_err:
        # Handle 429 explicit
        status_code = getattr(http_err.response, "status_code", None)
        body = getattr(http_err.response, "text", str(http_err))
        if status_code == 429 or (isinstance(body, str) and "Quota exceeded" in body):
            return None, f"Quota exceeded hoặc rate limit. Chi tiết: {body}"
        return None, f"Lỗi API văn bản: {body}"
    except Exception as e:
        return None, f"Lỗi API văn bản: {str(e)}"

def call_gemini_image(model, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {"contents":[{"role":"user","parts":[{"text": prompt}]}]}
    try:
        res = requests.post(url, json=payload, timeout=90)
        res.raise_for_status()
        data = res.json()
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []): 
                if "inlineData" in part and part["inlineData"]["mimeType"].startswith("image/"):
                    incr_api_count()
                    return part["inlineData"]["data"], None
        return None, "Không tìm thấy media (ảnh) trong phản hồi."
    except requests.exceptions.HTTPError as http_err:
        body = getattr(http_err.response, "text", str(http_err))
        if "Quota exceeded" in body or getattr(http_err.response, "status_code", None) == 429:
            return None, f"Quota exceeded hoặc rate limit. Chi tiết: {body}"
        return None, f"Lỗi API ảnh: {body}"
    except Exception as e:
        return None, f"Lỗi API ảnh: {str(e)}"

# --------------------------
# Utility: image store & TTS (unchanged)
# --------------------------
def store_image_entry(question_text, img_b64, style_key):
    img_id = str(uuid.uuid4())
    st.session_state.image_history.append({
        "id": img_id, "question": question_text,
        "b64": img_b64, "style": style_key,
        "time": datetime.utcnow().isoformat()
    })
    return img_id

def speak_text(text):
    try:
        from gtts import gTTS
        fp = io.BytesIO()
        clean_text = text.replace("**","").replace("$","").replace("\\","").replace("{","").replace("}","")
        tts = gTTS(text=clean_text, lang="vi")
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp.read(), format="audio/mp3")
    except Exception:
        st.warning("Không thể tạo giọng nói.")

# --------------------------
# Input handling helper
# --------------------------
def set_pending_action(action_type):
    q = st.session_state.user_input_area.strip()
    if not q:
        return
    st.session_state["temp_question"] = q
    st.session_state.user_input_area = ""
    st.session_state["pending_action"] = action_type

# --------------------------
# LOGIN INTERFACE (HIỆU ỨNG) - giữ nguyên UI
# --------------------------
if not st.session_state.user_name or not st.session_state.user_class:
    st.markdown("""
        <style>
        .login-title {font-size: 36px; color:#2c3e50; background:white; display:inline-block; padding:8px 15px; border-radius:8px; margin:10px; text-shadow:2px 2px 5px rgba(0,0,0,0.3); animation: fadeIn 1.5s ease-in-out;}
        .login-subtitle {font-size: 24px; color:#34495e; margin:10px; animation: fadeIn 2s ease-in-out;}
        .login-desc {font-size: 18px; color:#2c3e50; margin-top:5px; animation: fadeIn 2.5s ease-in-out;}
        @keyframes fadeIn {from {opacity:0; transform:translateY(-20px);} to {opacity:1; transform:translateY(0);} }
        </style>
        <div style="text-align:center; background: linear-gradient(to right,#a1c4fd,#c2e9fb); padding:40px; border-radius:12px; margin-bottom:20px;">
            <div style="font-size:100px; margin-bottom:15px;">🤖</div>
            <h1 class='login-title'>GIA SƯ ẢO CỦA BẠN</h1>
            <h3 class='login-subtitle'>ĐỀ TÀI NGHIÊN CỨU KHOA HỌC</h3>
            <p class='login-desc'>Nhập Họ và Tên cùng Lớp để bắt đầu trải nghiệm</p>
        </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns([1,1])
    with col1:
        name_input = st.text_input("Họ và tên", value=st.session_state.user_name)
    with col2:
        class_input = st.text_input("Lớp", value=st.session_state.user_class)
    if st.button("Đăng nhập", use_container_width=True):
        if name_input.strip() and class_input.strip():
            st.session_state.user_name = name_input.strip()
            st.session_state.user_class = class_input.strip()
            st.rerun()
        else:
            st.warning("Vui lòng nhập đủ Họ tên và Lớp.")
    st.stop()

# --------------------------
# SIDEBAR (giữ nguyên chức năng)
# --------------------------
with st.sidebar:
    st.markdown(f"### Xin chào, **{st.session_state.user_name}** - Lớp **{st.session_state.user_class}**")
    chosen_label = st.selectbox("Chọn model Gemini", list(MODEL_OPTIONS.keys()))
    st.session_state.chosen_model = MODEL_OPTIONS[chosen_label]
    style = st.selectbox("Phong cách ảnh", list(STYLE_PROMPT_MAP.keys()), index=0)
    tts_enabled = st.checkbox("Bật Text-to-Speech (Đọc lời giải)", value=st.session_state.get("tts_enabled", False))
    st.session_state["tts_enabled"] = tts_enabled
    st.session_state["style"] = style

    # show usage stats (helpful)
    st.markdown("---")
    st.markdown(f"**Yêu cầu API (phiên này):** {st.session_state.get('api_call_count',0)}")
    st.markdown(f"**Cache size:** {len(st.session_state.get('cache_order',[]))}")

# --------------------------
# MAIN UI
# --------------------------
with st.container():
    col_left, col_right = st.columns([3, 1])
    with col_right:
        st.subheader("📂 Nhật ký ảnh")
        for entry in reversed(st.session_state.image_history[-6:]):
            try:
                st.image(base64.b64decode(entry["b64"]), width=100)
            except Exception:
                st.caption("❌ Ảnh lỗi")
            st.caption(f"📝 {entry['question'][:30]}...")

    with col_left:
        st.markdown("<style> .chat-box {max-height:600px; overflow-y:auto; padding:10px;} </style>", unsafe_allow_html=True)
        chat_container = st.container()
        def show_chat():
            with chat_container:
                for msg in st.session_state.chat_history:
                    role = msg["role"]
                    color = "#e6f3ff" if role=="user" else "#f0e6ff"
                    st.markdown(f\"\"\"
                    <div style='background:{color}; padding:12px; border-radius:10px; margin-bottom:8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                        {msg['text']}
                    </div>\"\"\", unsafe_allow_html=True)
                    if msg.get("image_b64"):
                        try:
                            st.image(base64.b64decode(msg["image_b64"]), use_column_width=True)
                        except Exception:
                            st.error("Lỗi hiển thị ảnh.")
        show_chat()

# --------------------------
# API PROCESSING (optimized flow)
# --------------------------
if st.session_state.get("pending_action"):
    q = st.session_state.get("temp_question", "").strip()
    if not q:
        st.session_state["pending_action"] = ""
        st.session_state["temp_question"] = ""
    else:
        # common: append user question to chat history immediately for UX
        st.session_state.chat_history.append({"role":"user","text":q,"time":datetime.utcnow().isoformat()})

        # Throttle/spam protection
        if not can_call_api():
            st.session_state.chat_history.append({
                "role": "assistant",
                "text": "⏳ Bạn thao tác hơi nhanh hoặc đã vượt ngưỡng phiên. Vui lòng chờ một chút hoặc thử lại sau.",
                "time": datetime.utcnow().isoformat()
            })
            st.session_state["pending_action"] = ""
            st.session_state["temp_question"] = ""
            st.rerun()

        # Check cache
        cached = get_cached_answer(q, st.session_state.chosen_model)
        if cached:
            st.session_state.chat_history.append({"role":"assistant","text":cached,"time":datetime.utcnow().isoformat()})
            # optional TTS
            if st.session_state.get("tts_enabled"):
                speak_text(cached)
            st.session_state["pending_action"] = ""
            st.session_state["temp_question"] = ""
            st.rerun()

        # Prepare short history to send (very small)
        short_hist = compress_history_for_api(st.session_state.get("chat_history", []), max_turns=HISTORY_TO_SEND)

        # Call API
        if st.session_state["pending_action"] == "text":
            with st.spinner("⏳ Đang tạo lời giải..."):
                answer, err = call_gemini_text(st.session_state.chosen_model, q, short_history=short_hist)
                if err:
                    st.session_state.chat_history.append({"role":"assistant","text":f"❌ Lỗi: {err}","time":datetime.utcnow().isoformat()})
                else:
                    st.session_state.chat_history.append({"role":"assistant","text":answer,"time":datetime.utcnow().isoformat()})
                    # save to cache
                    try:
                        save_cache(q, st.session_state.chosen_model, answer)
                    except Exception:
                        pass
                    if st.session_state.get("tts_enabled"):
                        speak_text(answer)
        elif st.session_state["pending_action"] == "image":
            with st.spinner("🎨 Đang tạo ảnh minh họa..."):
                style_key = st.session_state.get("style", "Gia sư trẻ trung")
                # to save quota: avoid creating images if prompt too short or trivial
                if len(q) < 8:
                    st.session_state.chat_history.append({"role":"assistant","text":"❌ Vui lòng mô tả chi tiết hơn để tạo ảnh.","time":datetime.utcnow().isoformat()})
                else:
                    img_b64, img_err = call_gemini_image(st.session_state.chosen_model, f"{q} - style: {style_key}")
                    if img_err:
                        st.session_state.chat_history.append({"role":"assistant","text":f"❌ Lỗi tạo ảnh từ API: {img_err}","time":datetime.utcnow().isoformat()})
                    elif not img_b64:
                        st.session_state.chat_history.append({"role":"assistant","text":"❌ Lỗi: API không trả về dữ liệu ảnh hợp lệ.","time":datetime.utcnow().isoformat()})
                    else:
                        st.session_state.chat_history.append({
                            "role":"assistant","text":"**[Ảnh minh họa đã tạo]**","image_b64":img_b64,
                            "time":datetime.utcnow().isoformat()
                        })
                        store_image_entry(q, img_b64, style_key)

        # cleanup pending
        st.session_state["pending_action"] = ""
        st.session_state["temp_question"] = ""
        st.rerun()

# --------------------------
# USER INPUT
# --------------------------
user_q = st.text_area("Nhập câu hỏi của bạn:", height=120, key="user_input_area")
col1_btn, col2_btn = st.columns([1,1])
with col1_btn:
    st.button("Gửi câu hỏi", use_container_width=True, type="primary", on_click=set_pending_action, args=("text",))
with col2_btn:
    st.button("Tạo ảnh minh họa", use_container_width=True, on_click=set_pending_action, args=("image",))
