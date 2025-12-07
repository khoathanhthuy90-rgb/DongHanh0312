# app_gia_su_ao_final_optimal.py
import streamlit as st
import requests, base64, uuid, io, time
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

st.set_page_config(page_title="Gia Sư Ảo", layout="wide", page_icon="🤖")

# ======================
# SESSION STATE
# ======================
DEFAULT_KEYS = [
    "chat_history", "image_history", "chosen_model",
    "user_name", "user_class", "user_input_area",
    "pending_action", "temp_question", "tts_enabled", "style"
]

for key in DEFAULT_KEYS:
    if key not in st.session_state:
        st.session_state[key] = [] if "history" in key else ""

st.session_state.setdefault("tts_enabled", False)
CACHE_ANSWER = {}
LAST_CALL_TIME = 0

# ======================
# HELPERS
# ======================

# Giảm token bằng cách rút gọn lịch sử
def compress_history(history, max_len=4):
    return history[-max_len:]

# Cache câu hỏi trùng lặp
def get_cached_answer(prompt):
    return CACHE_ANSWER.get(prompt.strip().lower())

def save_cache(prompt, answer):
    CACHE_ANSWER[prompt.strip().lower()] = answer

# Chặn spam (1 req mỗi 3s)
def can_call_api():
    global LAST_CALL_TIME
    now = time.time()
    if now - LAST_CALL_TIME < 3:
        return False
    LAST_CALL_TIME = now
    return True

# Gọi API sinh văn bản
def call_gemini_text(model, user_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"

    user_name = st.session_state.get("user_name", "học sinh")
    user_class = st.session_state.get("user_class", "Chưa rõ")

    full_prompt = (
        f"{SYSTEM_INSTRUCTION}\n"
        f"Bạn đang hỗ trợ học sinh tên {user_name}, lớp {user_class}.\n"
        f"---\n"
        f"Câu hỏi: {user_prompt}"
    )

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": full_prompt}]}
        ]
    }

    try:
        res = requests.post(url, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text, None
    except Exception as e:
        return None, str(e)

# Gọi API sinh ảnh
def call_gemini_image(model, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {"contents":[{"role":"user","parts":[{"text": prompt}]}]}

    try:
        res = requests.post(url, json=payload, timeout=90)
        res.raise_for_status()
        data = res.json()

        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                if "inlineData" in part:
                    return part["inlineData"]["data"], None

        return None, "API không trả về hình."
    except Exception as e:
        return None, str(e)

# TTS
def speak_text(text):
    try:
        from gtts import gTTS
        fp = io.BytesIO()
        clean = text.replace("*", "").replace("$", "")
        gTTS(text=clean, lang="vi").write_to_fp(fp)
        fp.seek(0)
        st.audio(fp.read())
    except:
        st.warning("Không thể tạo giọng đọc.")

def set_pending_action(action_type):
    q = st.session_state.user_input_area.strip()
    if not q:
        return
    st.session_state.temp_question = q
    st.session_state.user_input_area = ""
    st.session_state.pending_action = action_type

# ======================
# LOGIN SCREEN
# ======================
if not st.session_state.user_name or not st.session_state.user_class:
    st.markdown("""
        <div style="text-align:center; padding:40px; background:#e8f3ff; border-radius:12px;">
            <h1 style="font-size:40px;">🤖 GIA SƯ ẢO CỦA BẠN</h1>
            <h3>Đề tài nghiên cứu khoa học</h3>
            <p>Hãy nhập họ tên và lớp để bắt đầu</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        name_input = st.text_input("Họ và tên")
    with col2:
        class_input = st.text_input("Lớp")

    if st.button("Bắt đầu", use_container_width=True):
        if name_input.strip() and class_input.strip():
            st.session_state.user_name = name_input.strip()
            st.session_state.user_class = class_input.strip()
            st.rerun()
        else:
            st.warning("Vui lòng nhập đủ thông tin.")
    st.stop()

# ======================
# SIDEBAR
# ======================
with st.sidebar:
    st.markdown(f"### 👋 Xin chào, **{st.session_state.user_name}** – Lớp **{st.session_state.user_class}**")

    label = st.selectbox("Model", list(MODEL_OPTIONS.keys()))
    st.session_state.chosen_model = MODEL_OPTIONS[label]

    st.session_state.style = st.selectbox("Phong cách ảnh", list(STYLE_PROMPT_MAP.keys()))

    st.session_state.tts_enabled = st.checkbox("Bật Text-to-Speech")

# ======================
# UI CHÍNH
# ======================
col_left, col_right = st.columns([3, 1])

with col_right:
    st.subheader("📘 Nhật ký ảnh")
    for entry in reversed(st.session_state.image_history[-6:]):
        try:
            st.image(base64.b64decode(entry["b64"]), width=110)
        except:
            st.text("❌ ảnh lỗi")

with col_left:
    chat_container = st.container()

    def render_chat():
        for msg in st.session_state.chat_history:
            bg = "#dff2ff" if msg["role"]=="user" else "#f5e8ff"
            st.markdown(
                f"""
                <div style='background:{bg}; padding:12px; border-radius:12px; margin-bottom:8px;'>
                    {msg["text"]}
                </div>
                """,
                unsafe_allow_html=True
            )
            if msg.get("image_b64"):
                st.image(base64.b64decode(msg["image_b64"]), use_column_width=True)

    render_chat()

# ======================
# XỬ LÝ YÊU CẦU
# ======================
if st.session_state.pending_action:

    q = st.session_state.temp_question

    if st.session_state.pending_action == "text":
        st.session_state.chat_history.append({"role":"user","text":q})

        # ⛔ Chặn spam
        if not can_call_api():
            st.session_state.chat_history.append({
                "role":"assistant",
                "text":"⏳ Bạn thao tác nhanh quá. Chờ 3 giây rồi thử lại nhé!"
            })
        else:
            # ✔ Cache
            cached = get_cached_answer(q)
            if cached:
                st.session_state.chat_history.append({"role":"assistant","text":cached})
            else:
                with st.spinner("Đang tạo lời giải..."):
                    answer, err = call_gemini_text(st.session_state.chosen_model, q)

                if err:
                    st.session_state.chat_history.append({"role":"assistant","text":f"❌ Lỗi: {err}"})
                else:
                    st.session_state.chat_history.append({"role":"assistant","text":answer})
                    save_cache(q, answer)

                    if st.session_state.tts_enabled:
                        speak_text(answer)

    elif st.session_state.pending_action == "image":
        st.session_state.chat_history.append({"role":"user","text":f"[Yêu cầu tạo ảnh] {q}"})

        with st.spinner("Đang tạo ảnh..."):
            style = STYLE_PROMPT_MAP[st.session_state.style]
            img_b64, err = call_gemini_image(
                st.session_state.chosen_model,
                f"{q}. Style: {style}"
            )

        if err or not img_b64:
            st.session_state.chat_history.append({"role":"assistant","text":"❌ Lỗi tạo ảnh."})
        else:
            st.session_state.chat_history.append({
                "role":"assistant",
                "text":"Ảnh đã tạo:",
                "image_b64": img_b64
            })
            st.session_state.image_history.append({
                "id": str(uuid.uuid4()),
                "question": q,
                "b64": img_b64,
                "style": st.session_state.style,
                "time": datetime.utcnow().isoformat()
            })

    st.session_state.pending_action = ""
    st.session_state.temp_question = ""
    st.rerun()

# ======================
# INPUT
# ======================
st.text_area("Nhập câu hỏi:", key="user_input_area", height=120)

c1, c2 = st.columns(2)
with c1:
    st.button("Gửi câu hỏi", on_click=set_pending_action, args=("text",))
with c2:
    st.button("Tạo ảnh minh họa", on_click=set_pending_action, args=("image",))
