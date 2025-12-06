# app_gia_su_ao_v_final_modern_v3.py (Chỉnh header hiển thị chữ)
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

# --------------------------
# SESSION INIT
# --------------------------
for key in ["chat_history", "image_history", "chosen_model"]:
    if key not in st.session_state:
        st.session_state[key] = []
        
for key in ["user_name", "user_class", "user_input_area"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# --------------------------
# LOGIN HEADER (Chỉ sửa hiển thị chữ, bỏ hình)
# --------------------------
if not st.session_state.user_name or not st.session_state.user_class:
    st.markdown("""
    <div style="text-align:center; margin-bottom:20px;">
        <h2 style="color:#2c3e50; font-size:28px; margin:0; background:white; display:inline-block; padding:5px 10px; border-radius:5px;">
            GIA SƯ ẢO CỦA BẠN
        </h2>
        <h4 style="color:#7f8c8d; margin:5px 0 0 0;">ĐỀ TÀI NGHIÊN CỨU KHOA HỌC</h4>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1,1])
    with col1: name_input = st.text_input("Họ và tên")
    with col2: class_input = st.text_input("Lớp")
    if st.button("Đăng nhập", use_container_width=True):
        if name_input.strip() and class_input.strip():
            st.session_state.user_name = name_input.strip()
            st.session_state.user_class = class_input.strip()
            st.rerun()
        else:
            st.warning("Vui lòng nhập đủ Họ tên và Lớp.")
    st.stop()

# --------------------------
# HELPERS
# --------------------------
def call_gemini_text(model, user_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    full_prompt = f"{SYSTEM_INSTRUCTION}\n\n[Đề bài]: {user_prompt}"
    payload = {
        "contents": [{"role":"user", "parts":[{"text": full_prompt}]}],
    }
    try:
        res = requests.post(url, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text, None
    except Exception as e:
        error_detail = res.text if 'res' in locals() else str(e)
        return None, f"Lỗi API văn bản: {error_detail}"

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
                    return part["inlineData"]["data"], None
        return None, "Không tìm thấy media (ảnh) trong phản hồi."
    except Exception as e:
        error_detail = res.text if 'res' in locals() else str(e)
        return None, f"Lỗi API ảnh: {error_detail}"

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
        clean_text = text.replace("**","").replace("$","").replace("\\","")
        tts = gTTS(text=clean_text, lang="vi")
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp.read(), format="audio/mp3")
    except ImportError:
        st.warning("Không thể tạo giọng nói. Vui lòng cài đặt gTTS: `pip install gTTS`.")
    except Exception:
        st.warning("Không thể tạo giọng nói.")

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
with st.container():
    col_left, col_right = st.columns([3,1])
    with col_right:
        st.subheader("📂 Nhật ký ảnh")
        for entry in reversed(st.session_state.image_history[-6:]):
            st.image(base64.b64decode(entry["b64"]), width=100)
            st.caption(f"📝 {entry['question'][:30]}...")

    with col_left:
        st.markdown("<style> .chat-box {max-height:500px; overflow-y:auto; padding:10px;} </style>", unsafe_allow_html=True)
        chat_container = st.container()
        for msg in reversed(st.session_state.chat_history):
            role = msg["role"]
            color = "#e6f3ff" if role=="user" else "#f0e6ff"
            st.markdown(f"""
            <div style='background:{color}; padding:12px; border-radius:10px; margin-bottom:8px; box-shadow:0 2px 4px rgba(0,0,0,0.05);'>
                {msg['text']}
            </div>""", unsafe_allow_html=True)
            if msg.get("image_b64"):
                st.image(base64.b64decode(msg["image_b64"]), use_column_width=True)

# --------------------------
# Hộp nhập câu hỏi dưới cùng
# --------------------------
user_q = st.text_area("Nhập câu hỏi của bạn:", height=120, key="user_input_area")
col1_btn, col2_btn = st.columns([1,1])

with col1_btn:
    if st.button("Gửi câu hỏi", use_container_width=True, type="primary"):
        q = st.session_state.user_input_area.strip()
        if q:
            st.session_state.user_input_area = ""
            st.session_state.chat_history.append({"role":"user","text":q,"time":datetime.utcnow().isoformat()})
            with st.spinner("⏳ Đang tạo lời giải..."):
                answer, err = call_gemini_text(st.session_state.chosen_model, q)
                if err:
                    st.session_state.chat_history.append({"role":"assistant","text":f"❌ Lỗi: {err}","time":datetime.utcnow().isoformat()})
                else:
                    st.session_state.chat_history.append({"role":"assistant","text":answer,"time":datetime.utcnow().isoformat()})
                    if tts_enabled: speak_text(answer)
            st.rerun()

with col2_btn:
    if st.button("Tạo ảnh minh họa", use_container_width=True):
        q = st.session_state.user_input_area.strip()
        if q:
            st.session_state.user_input_area = ""
            st.session_state.chat_history.append({"role":"user","text":f"[Yêu cầu tạo ảnh]: {q}","time":datetime.utcnow().isoformat()})
            with st.spinner("🎨 Đang tạo ảnh minh họa..."):
                img_b64, img_err = call_gemini_image(st.session_state.chosen_model, f"{q} - style: {style}")
                if img_err:
                    st.session_state.chat_history.append({"role":"assistant","text":f"❌ Lỗi tạo ảnh: {img_err}"})
                else:
                    st.session_state.chat_history.append({"role":"assistant","text":"**[Ảnh minh họa đã tạo]**","image_b64":img_b64,"time":datetime.utcnow().isoformat()})
                    store_image_entry(q, img_b64, style)
            st.rerun()
