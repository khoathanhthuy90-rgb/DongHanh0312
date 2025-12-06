# app_gia_su_ao_v1beta_final.py
import streamlit as st
import requests, base64, uuid, io
from datetime import datetime

# --------------------------
# CONFIG
# --------------------------
API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
if not API_KEY:
    st.error("⚠️ Thiếu GEMINI_API_KEY trong .streamlit/secrets.toml")
    st.stop()

MODEL_OPTIONS = {
    "Gemini 2.0 Flash": "gemini-2.0-flash",
    "Gemini 2.0 Pro": "gemini-2.0-pro-exp",
    "Gemini 1.5 Flash": "gemini-1.5-flash"
}

SYSTEM_INSTRUCTION = (
    "Bạn là gia sư ảo thân thiện, giải bài cho học sinh cấp 2–3. "
    "Trình bày rõ ràng, dùng LaTeX khi cần. Nếu có ảnh, sử dụng ảnh để giải thích."
)

STYLE_PROMPT_MAP = {
    "Gia sư trẻ trung": "young friendly tutor, smiling, colorful, modern, cartoon-realistic style"
}

st.set_page_config(page_title="Gia Sư Ảo", layout="wide", page_icon="🤖")

# --------------------------
# SESSION INIT
# --------------------------
for key in ["chat_history","image_history","user_input","chosen_model","user_name","user_class"]:
    if key not in st.session_state:
        st.session_state[key] = "" if "input" in key or "name" in key or "class" in key else []

# --------------------------
# LOGIN
# --------------------------
if not st.session_state.user_name or not st.session_state.user_class:
    st.markdown("""
        <div style="text-align:center; background: linear-gradient(to right, #74ebd5, #ACB6E5); padding:30px; border-radius:12px; margin-bottom:20px;">
            <img src="https://i.imgur.com/4AiXzf8.png" width="120" style="border-radius:50%;"/>
            <h1 style='color:#2c3e50; margin:10px;'>👨‍🏫 GIA SƯ ẢO CỦA BẠN</h1>
            <h4 style='color:#7f8c8d; margin:5px;'>ĐỀ TÀI NGHIÊN CỨU KHOA HỌC</h4>
        </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns([1,1])
    with col1: name_input = st.text_input("Họ và tên")
    with col2: class_input = st.text_input("Lớp")
    if st.button("Đăng nhập", use_container_width=True):
        if name_input.strip() and class_input.strip():
            st.session_state.user_name = name_input.strip()
            st.session_state.user_class = class_input.strip()
            st.success(f"Chào {st.session_state.user_name} - Lớp {st.session_state.user_class}! Bạn có thể bắt đầu hỏi bài.")
        else:
            st.warning("Vui lòng nhập đủ Họ tên và Lớp.")
    st.stop()

# --------------------------
# HELPERS
# --------------------------
def call_gemini_text(model, user_prompt):
    """Gọi Gemini v1beta chuẩn với prompt.messages"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {
        "prompt": {
            "messages": [
                {"author":"system","content":[{"type":"text","text": SYSTEM_INSTRUCTION}]},
                {"author":"user","content":[{"type":"text","text": user_prompt}]}
            ]
        },
        "temperature":0.2,
        "candidate_count":1
    }
    try:
        res = requests.post(url, json=payload, timeout=45)
        res.raise_for_status()
        data = res.json()
        text = data["candidates"][0]["content"][0].get("text","")
        return text, None
    except Exception as e:
        return None, f"Lỗi API: {e}"

def call_gemini_image(model, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {
        "prompt": {
            "messages": [
                {"author":"user","content":[{"type":"text","text": prompt}]}
            ]
        },
        "temperature":0.2,
        "candidate_count":1
    }
    try:
        res = requests.post(url, json=payload, timeout=90)
        res.raise_for_status()
        data = res.json()
        for p in data["candidates"][0]["content"]:
            if "media" in p: return p["media"]["data"], None
        return None, "Không tìm thấy media"
    except Exception as e: return None, str(e)

def store_image_entry(question_text, img_b64, style_key):
    img_id = str(uuid.uuid4())
    st.session_state.image_history.append({
        "id": img_id, "question": question_text, "b64": img_b64, "style": style_key,
        "time": datetime.utcnow().isoformat()
    })
    return img_id

def speak_text(text):
    try:
        from gtts import gTTS
        fp = io.BytesIO()
        tts = gTTS(text=text, lang="vi")
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp.read(), format="audio/mp3")
    except Exception as e:
        st.warning("Không thể tạo giọng nói: " + str(e))

# --------------------------
# SIDEBAR
# --------------------------
with st.sidebar:
    st.markdown(f"### Xin chào, {st.session_state.user_name} - Lớp {st.session_state.user_class}")
    chosen_label = st.selectbox("Chọn model Gemini", list(MODEL_OPTIONS.keys()))
    st.session_state.chosen_model = MODEL_OPTIONS[chosen_label]
    style = st.selectbox("Phong cách ảnh", list(STYLE_PROMPT_MAP.keys()), index=0)
    tts_enabled = st.checkbox("Bật Text-to-Speech", value=False)

# --------------------------
# MAIN UI
# --------------------------
col_left, col_right = st.columns([3,2])
with col_left:
    st.subheader("Nhập đề bài / câu hỏi")
    user_q = st.text_area("", value=st.session_state.get("user_input",""), height=150)
    st.session_state.user_input = user_q

    btn_send = st.button("Gửi câu hỏi")
    btn_image = st.button("Tạo ảnh minh họa")

    chat_container = st.empty()
    def show_chat():
        with chat_container:
            st.markdown("""
                <style>
                .chat-box {border-radius:12px; padding:12px; max-height:500px; overflow-y:auto; background:#fefefe; box-shadow:0 6px 18px rgba(0,0,0,0.12);}
                .user-msg {background:#ffd1dc; padding:10px; border-radius:10px; margin-bottom:6px;}
                .ai-msg {background:#d0f0fd; padding:10px; border-radius:10px; margin-bottom:6px;}
                </style>
                <div class="chat-box">
            """, unsafe_allow_html=True)
            for m in st.session_state.chat_history[-20:]:
                cls = "ai-msg" if m["role"]=="assistant" else "user-msg"
                msg_text = m['text'].replace("\n","<br>")
                st.markdown(f"<div class='{cls}'>{msg_text}</div>", unsafe_allow_html=True)
                if m.get("image_b64"):
                    st.image(base64.b64decode(m["image_b64"]), use_column_width=True)
                    st.download_button("📥 Tải ảnh", data=base64.b64decode(m["image_b64"]),
                                       file_name=f"minh_hoa_{uuid.uuid4().hex[:6]}.png", mime="image/png")
            st.markdown("</div>", unsafe_allow_html=True)
    show_chat()

# --------------------------
# ACTION: Gửi câu hỏi
# --------------------------
if btn_send and user_q.strip():
    # Hiển thị câu hỏi ngay
    st.session_state.chat_history.append({"role":"user","text":user_q,"time":datetime.utcnow().isoformat()})
    show_chat()

    with st.spinner("⏳ Đang tạo lời giải..."):
        answer_text, err = call_gemini_text(st.session_state.chosen_model, user_q)
        if err: st.error(err)
        else:
            st.session_state.chat_history.append({"role":"assistant","text":answer_text,"time":datetime.utcnow().isoformat()})
            if tts_enabled: speak_text(answer_text)
    show_chat()

# --------------------------
# ACTION: Tạo ảnh minh họa
# --------------------------
if btn_image and user_q.strip():
    img_prompt = f"Educational illustration with style '{style}': {user_q}."
    with st.spinner("🎨 Đang tạo ảnh minh họa..."):
        img_b64, img_err = call_gemini_image(st.session_state.chosen_model, img_prompt)
        if img_err: st.error("Không tạo được ảnh: " + img_err)
        else:
            st.session_state.chat_history.append({
                "role":"assistant",
                "text":"[Ảnh minh họa]",
                "image_b64": img_b64,
                "time": datetime.utcnow().isoformat()
            })
            store_image_entry(user_q, img_b64, style)
    show_chat()

with col_right:
    st.subheader("📂 Nhật ký ảnh")
    for entry in reversed(st.session_state.image_history[-6:]):
        st.image(base64.b64decode(entry["b64"]), width=160)
        st.write(f"📝 {entry['question'][:50]}...")
