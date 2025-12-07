# app_gia_su_ao_final_optimal_v2.py
import streamlit as st
import requests
import base64
import uuid
import io
import time
import json
from datetime import datetime

# ======================
# CONFIG
# ======================
API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
if not API_KEY:
    st.error("⚠️ Thiếu GEMINI_API_KEY trong .streamlit/secrets.toml.")
    st.stop()

MODEL_OPTIONS = {
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
}

SYSTEM_INSTRUCTION = (
    "Bạn là gia sư ảo thân thiện, giải bài cho học sinh cấp 2–3. "
    "Trình bày rõ ràng, dùng LaTeX khi cần."
)

STYLE_PROMPT_MAP = {
    "Gia sư trẻ trung": "young friendly tutor, smiling, colorful, modern, cartoon-realistic style"
}

# Tuning
API_COOLDOWN_SECONDS = 3            # 3s giữa 2 lần gọi API trong cùng phiên (throttle)
SESSION_REQUEST_SOFT_LIMIT = 600    # soft cap calls per session (adjustable)
HISTORY_TO_SEND = 2                 # send last N messages to API (minimize token)
RETRY_ON_429 = 2                    # số lần retry khi gặp 429
RETRY_BASE_DELAY = 2                # giây cơ bản cho backoff

st.set_page_config(page_title="Gia Sư Ảo", layout="wide", page_icon="🤖")

# ======================
# SESSION INIT
# ======================
DEFAULT_KEYS = [
    "chat_history", "image_history", "chosen_model",
    "user_name", "user_class", "user_input_area",
    "pending_action", "temp_question", "tts_enabled", "style",
    "api_call_count", "last_api_call_time"
]

for key in DEFAULT_KEYS:
    if key not in st.session_state:
        # history keys are lists, others default empty string / false or number
        if key in ("chat_history", "image_history"):
            st.session_state[key] = []
        elif key == "chosen_model":
            st.session_state[key] = MODEL_OPTIONS[list(MODEL_OPTIONS.keys())[0]]
        elif key == "tts_enabled":
            st.session_state[key] = False
        elif key == "api_call_count":
            st.session_state[key] = 0
        elif key == "last_api_call_time":
            st.session_state[key] = 0.0
        else:
            st.session_state[key] = ""

# Persistent in-memory cache across reruns (fast) - use st.cache_data to persist between sessions/runs
@st.cache_data(ttl=60*60*24)  # cache lasts 1 day by default
def _init_cache():
    return {}

# fetch the persistent cache object (note: returns a copy; we'll manage writes via helper)
CACHE_STORE = _init_cache()

def cache_get(key):
    return CACHE_STORE.get(key)

def cache_set(key, value):
    # mutate and then re-set cache via dummy function re-init (st.cache_data returns copy, so we flush via global approach)
    CACHE_STORE[key] = value
    return True

# ======================
# HELPERS: throttle, history compress, key helper
# ======================
def can_call_api():
    now = time.time()
    last = st.session_state.get("last_api_call_time", 0.0)
    if now - last < API_COOLDOWN_SECONDS:
        return False
    if st.session_state.get("api_call_count", 0) >= SESSION_REQUEST_SOFT_LIMIT:
        return False
    # allow
    st.session_state["last_api_call_time"] = now
    return True

def incr_api_count():
    st.session_state["api_call_count"] = st.session_state.get("api_call_count", 0) + 1

def make_cache_key(prompt: str, model: str):
    # normalize prompt small
    return (model + "::" + prompt.strip().lower())[:2000]

def compress_history_for_api(full_history, max_turns=HISTORY_TO_SEND):
    """
    Return a tiny list of last max_turns messages for sending to API.
    Each item: {"role": "user"/"assistant", "text": "..."}
    """
    if not full_history:
        return []
    recent = full_history[-max_turns:]
    simplified = []
    for m in recent:
        role = m.get("role", "user")
        text = m.get("text", "")
        # strip image placeholders and long texts
        if m.get("image_b64"):
            text = "[Ảnh đã gửi]"  # placeholder
        # limit length
        if len(text) > 1000:
            text = text[:1000] + "..."
        simplified.append({"role": role, "text": text})
    return simplified

# ======================
# API CALLS (with retry/backoff & minimal prompt)
# ======================
def call_gemini_text(model, user_prompt, short_history=None):
    """
    Calls Gemini generateContent with:
    - minimal system instruction
    - personal context
    - short_history (optional)
    - user_prompt
    Retries on 429 with exponential backoff (small).
    Returns (text, error_str_or_None)
    """
    user_name = st.session_state.get("user_name", "học sinh")
    user_class = st.session_state.get("user_class", "Chưa rõ")
    personal_context = f"Học sinh: {user_name} (Lớp {user_class}). Trả lời ngắn gọn, rõ ràng."

    # Build a compact textual prompt; keep minimal to save tokens
    content_lines = [SYSTEM_INSTRUCTION, personal_context]
    if short_history:
        for m in short_history:
            content_lines.append(f"{m['role'].upper()}: {m['text']}")
    content_lines.append(f"USER: {user_prompt}")

    compact_prompt = "\n".join(content_lines)

    payload = {"contents": [{"role": "user", "parts": [{"text": compact_prompt}]}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"

    for attempt in range(RETRY_ON_429 + 1):
        try:
            response = requests.post(url, json=payload, timeout=60)
            # Raise for HTTP errors
            response.raise_for_status()
            data = response.json()
            # Defensive extraction
            text = None
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                # fallback: stringify body
                text = json.dumps(data)
            incr_api_count()
            return text, None
        except requests.exceptions.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", None)
            body = getattr(http_err.response, "text", str(http_err))
            # handle 429 explicitly with backoff
            if status == 429 or "Quota exceeded" in body or "Too Many Requests" in body:
                if attempt < RETRY_ON_429:
                    # small exponential backoff
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    return None, f"Quota exceeded / Too Many Requests. Vui lòng chờ hoặc chuyển model / nâng cấp API key. Chi tiết: {body}"
            else:
                return None, f"Lỗi API văn bản: HTTP {status} - {body}"
        except Exception as e:
            return None, f"Lỗi API văn bản: {str(e)}"

def call_gemini_image(model, prompt):
    """
    Call Gemini to generate image-like data (as in your previous logic).
    Returns (b64data, error)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if "inlineData" in part and part["inlineData"].get("mimeType", "").startswith("image/"):
                    incr_api_count()
                    return part["inlineData"]["data"], None
        return None, "API không trả về ảnh hợp lệ."
    except requests.exceptions.HTTPError as http_err:
        body = getattr(http_err.response, "text", str(http_err))
        if getattr(http_err.response, "status_code", None) == 429 or "Quota exceeded" in body:
            return None, f"Quota exceeded / Too Many Requests: {body}"
        return None, f"Lỗi API ảnh: {body}"
    except Exception as e:
        return None, f"Lỗi API ảnh: {str(e)}"

# ======================
# UTIL: image store & TTS
# ======================
def store_image_entry(question_text, img_b64, style_key):
    img_id = str(uuid.uuid4())
    st.session_state.image_history.append({
        "id": img_id,
        "question": question_text,
        "b64": img_b64,
        "style": style_key,
        "time": datetime.utcnow().isoformat()
    })
    return img_id

def speak_text(text):
    try:
        from gtts import gTTS
        fp = io.BytesIO()
        clean_text = text.replace("**", "").replace("$", "").replace("\\", "")
        gTTS(text=clean_text, lang="vi").write_to_fp(fp)
        fp.seek(0)
        st.audio(fp.read(), format="audio/mp3")
    except Exception:
        st.warning("Không thể tạo giọng nói.")

def set_pending_action(action_type):
    q = st.session_state.user_input_area.strip()
    if not q:
        return
    st.session_state.temp_question = q
    st.session_state.user_input_area = ""
    st.session_state.pending_action = action_type

# ======================
# LOGIN SCREEN (unchanged look)
# ======================
if not st.session_state.user_name or not st.session_state.user_class:
    st.markdown("""
        <style>
        .login-title {font-size: 36px; color:#2c3e50; background:white; display:inline-block; padding:8px 15px; border-radius:8px; margin:10px; text-shadow:2px 2px 5px rgba(0,0,0,0.15); animation: fadeIn 1.2s ease-in-out;}
        .login-subtitle {font-size: 20px; color:#34495e; margin:10px; animation: fadeIn 1.5s ease-in-out;}
        @keyframes fadeIn {from {opacity:0; transform:translateY(-12px);} to {opacity:1; transform:translateY(0);} }
        </style>
        <div style="text-align:center; background: linear-gradient(to right,#a1c4fd,#c2e9fb); padding:36px; border-radius:12px; margin-bottom:18px;">
            <div style="font-size:80px; margin-bottom:10px;">🤖</div>
            <h1 class='login-title'>GIA SƯ ẢO CỦA BẠN</h1>
            <h3 class='login-subtitle'>ĐỀ TÀI NGHIÊN CỨU KHOA HỌC</h3>
            <p style="color:#2c3e50;">Nhập Họ và Tên và Lớp để bắt đầu</p>
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
            st.warning("Vui lòng nhập Họ và Tên và Lớp.")
    st.stop()

# ======================
# SIDEBAR
# ======================
with st.sidebar:
    st.markdown(f"### Xin chào, **{st.session_state.user_name}** - Lớp **{st.session_state.user_class}**")
    chosen_label = st.selectbox("Chọn model Gemini", list(MODEL_OPTIONS.keys()))
    st.session_state.chosen_model = MODEL_OPTIONS[chosen_label]
    style = st.selectbox("Phong cách ảnh", list(STYLE_PROMPT_MAP.keys()), index=0)
    st.session_state.style = style
    st.session_state.tts_enabled = st.checkbox("Bật Text-to-Speech (Đọc lời giải)", value=st.session_state.get("tts_enabled", False))
    st.markdown("---")
    st.markdown(f"**Yêu cầu API (phiên này):** {st.session_state.get('api_call_count', 0)}")
    st.markdown(f"**Cache local (gần đây):** {len(CACHE_STORE)}")

# ======================
# MAIN UI
# ======================
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
                    role = msg.get("role", "assistant")
                    color = "#e6f3ff" if role == "user" else "#f0e6ff"
                    st.markdown(f"""
                    <div style='background:{color}; padding:12px; border-radius:10px; margin-bottom:8px; box-shadow: 0 2px 4px rgba(0,0,0,0.03);'>
                        {msg.get('text','')}
                    </div>""", unsafe_allow_html=True)
                    if msg.get("image_b64"):
                        try:
                            st.image(base64.b64decode(msg["image_b64"]), use_column_width=True)
                        except Exception:
                            st.error("Lỗi hiển thị ảnh.")
        show_chat()

# ======================
# API PROCESSING (optimized flow)
# ======================
if st.session_state.get("pending_action"):
    q = st.session_state.get("temp_question", "").strip()
    if not q:
        st.session_state["pending_action"] = ""
        st.session_state["temp_question"] = ""
    else:
        # Append user to history (UX)
        st.session_state.chat_history.append({"role": "user", "text": q, "time": datetime.utcnow().isoformat()})

        # Throttle / spam protection
        if not can_call_api():
            st.session_state.chat_history.append({
                "role": "assistant",
                "text": "⏳ Bạn thao tác hơi nhanh hoặc đã vượt ngưỡng phiên. Vui lòng đợi vài giây rồi thử lại.",
                "time": datetime.utcnow().isoformat()
            })
            st.session_state.pending_action = ""
            st.session_state.temp_question = ""
            st.rerun()

        # Check cache
        cache_key = make_cache_key(q, st.session_state.chosen_model)
        cached = cache_get(cache_key)
        if cached:
            st.session_state.chat_history.append({"role": "assistant", "text": cached, "time": datetime.utcnow().isoformat()})
            if st.session_state.get("tts_enabled"):
                speak_text(cached)
            st.session_state.pending_action = ""
            st.session_state.temp_question = ""
            st.rerun()

        # Prepare minimal short history for API
        short_hist = compress_history_for_api(st.session_state.get("chat_history", []), max_turns=HISTORY_TO_SEND)

        # Text request
        if st.session_state.pending_action == "text":
            with st.spinner("⏳ Đang tạo lời giải..."):
                answer, err = call_gemini_text(st.session_state.chosen_model, q, short_history=short_hist)
                if err:
                    st.session_state.chat_history.append({"role": "assistant", "text": f"❌ Lỗi: {err}", "time": datetime.utcnow().isoformat()})
                else:
                    st.session_state.chat_history.append({"role": "assistant", "text": answer, "time": datetime.utcnow().isoformat()})
                    # Save to persistent cache
                    try:
                        cache_set(cache_key, answer)
                    except Exception:
                        pass
                    if st.session_state.get("tts_enabled"):
                        speak_text(answer)

        # Image request
        elif st.session_state.pending_action == "image":
            with st.spinner("🎨 Đang tạo ảnh minh họa..."):
                style_key = st.session_state.get("style", "Gia sư trẻ trung")
                # Require a somewhat detailed prompt to avoid trivial calls
                if len(q) < 8:
                    st.session_state.chat_history.append({"role": "assistant", "text": "❌ Vui lòng mô tả chi tiết hơn để tạo ảnh.", "time": datetime.utcnow().isoformat()})
                else:
                    img_b64, img_err = call_gemini_image(st.session_state.chosen_model, f"{q} - style: {style_key}")
                    if img_err:
                        st.session_state.chat_history.append({"role": "assistant", "text": f"❌ Lỗi tạo ảnh: {img_err}", "time": datetime.utcnow().isoformat()})
                    else:
                        st.session_state.chat_history.append({"role": "assistant", "text": "**[Ảnh minh họa đã tạo]**", "image_b64": img_b64, "time": datetime.utcnow().isoformat()})
                        store_image_entry(q, img_b64, style_key)

        # cleanup
        st.session_state.pending_action = ""
        st.session_state.temp_question = ""
        st.rerun()

# ======================
# USER INPUT
# ======================
st.text_area("Nhập câu hỏi của bạn:", height=120, key="user_input_area")
col1_btn, col2_btn = st.columns([1,1])
with col1_btn:
    st.button("Gửi câu hỏi", use_container_width=True, type="primary", on_click=set_pending_action, args=("text",))
with col2_btn:
    st.button("Tạo ảnh minh họa", use_container_width=True, on_click=set_pending_action, args=("image",))
