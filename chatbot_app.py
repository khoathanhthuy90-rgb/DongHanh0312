# app.py (Professional UI + Login)
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
    "Gemini 2.0 Flash (nhanh)": "gemini-2.0-flash",
    "Gemini 2.0 Pro (mạnh)": "gemini-2.0-pro-exp",
    "Gemini 1.5 Flash": "gemini-1.5-flash"
}

SYSTEM_INSTRUCTION = "Bạn là gia sư ảo thân thiện, giải bài cho học sinh cấp 2–3. Trình bày rõ ràng, dùng LaTeX cho công thức khi cần. Nếu có ảnh, sử dụng ảnh để giải thích."

STYLE_PROMPT_MAP = {
    "Gia sư trẻ trung": "young friendly tutor, smiling, colorful, modern, cartoon-realistic style"
}

st.set_page_config(page_title="Gia Sư Ảo – Minh họa", layout="wide", page_icon="🤖")

# --------------------------
# SESSION INIT
# --------------------------
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "image_history" not in st.session_state: st.session_state.image_history = []
if "user_input" not in st.session_state: st.session_state.user_input = ""
if "chosen_model" not in st.session_state: st.session_state.chosen_model = list(MODEL_OPTIONS.values())[0]
if "user_name" not in st.session_state: st.session_state.user_name = ""
if "user_class" not in st.session_state: st.session_state.user_class = ""

# --------------------------
# LOGIN
# --------------------------
if not st.session_state.user_name or not st.session_state.user_class:
    st.markdown("<h1 style='text-align:center; color:#1f4e79'>👨‍🏫 GIA SƯ ẢO CỦA BẠN</h1>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center; color:gray'>ĐĂNG NHẬP TRƯỚC KHI SỬ DỤNG</h4>", unsafe_allow_html=True)
    col1, col2 = st.columns([1,1])
    with col1: name_input = st.text_input("Họ và tên")
    with col2: class_input = st.text_input("Lớp")
    if st.button("Đăng nhập"):
        if name_input.strip() and class_input.strip():
            st.session_state.user_name = name_input.strip()
            st.session_state.user_class = class_input.strip()
            st.success(f"Chào {st.session_state.user_name} - Lớp {st.session_state.user_class}! Bạn có thể bắt đầu hỏi bài.")
        else:
            st.warning("Vui lòng nhập đủ Họ tên và Lớp trước khi đăng nhập.")
    st.stop()

# --------------------------
# HELPERS
# --------------------------
def text_api_url(model): return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"

def call_gemini_text(model, user_prompt, image_b64_inline=None):
    url = text_api_url(model)
    contents = [{"role":"user","parts":[{"text":SYSTEM_INSTRUCTION}]}]
    parts = []
    if image_b64_inline: parts.append({"inlineData":{"mimeType":"image/png","data":image_b64_inline}})
    parts.append({"text": user_prompt})
    contents.append({"role":"user","parts":parts})
    try:
        res = requests.post(url, json={"contents":contents}, timeout=45)
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"], None
    except Exception as e:
        return None, str(e)

def call_gemini_image(model, prompt):
    url = text_api_url(model)
    payload = {"contents":[{"role":"user","parts":[{"text":prompt}]}]}
    try:
        res = requests.post(url, json=payload, timeout=90)
        data = res.json()
        for p in data["candidates"][0]["content"]["parts"]:
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
# HEADER
# --------------------------
st.markdown("<h1 style='text-align:center; color:#1f4e79'>👨‍🏫 GIA SƯ ẢO CỦA BẠN</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center; color:gray'>ĐỀ TÀI NGHIÊN CỨU KHOA HỌC</h4>", unsafe_allow_html=True)
st.image("https://images.unsplash.com/photo-1596496053414-8c6a4d3b8927?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=400", width=200)

# --------------------------
# MAIN UI
# --------------------------
col_left, col_right = st.columns([3,2])
with col_left:
    st.subheader("Nhập đề bài / câu hỏi")
    user_q = st.text_area("Nhập đề bài hoặc câu hỏi:", value=st.session_state.get("user_input",""), height=160)
    st.session_state.user_input = user_q
    btn_send = st.button("Gửi & Sinh ảnh")

with col_right:
    with st.expander("💬 Nhật ký nhanh"):
        if st.session_state.chat_history:
            for m in st.session_state.chat_history[-10:]:
                role_color = "#d1e7dd" if m["role"]=="assistant" else "#f8d7da"
                st.markdown(f"<div style='background:{role_color};padding:10px;border-radius:8px;margin-bottom:5px'><b>{m['role'].capitalize()}:</b> {m['text']}</div>", unsafe_allow_html=True)
    with st.expander("📂 Nhật ký ảnh"):
        if st.session_state.image_history:
            for entry in reversed(st.session_state.image_history[-6:]):
                st.image(base64.b64decode(entry["b64"]), width=160)
                st.write(f"📝 {entry['question'][:80]}...")

# --------------------------
# ACTION: Send & Auto Image
# --------------------------
if btn_send and user_q.strip():
    with st.spinner("⏳ Đang tạo lời giải..."):
        answer_text, err = call_gemini_text(st.session_state.chosen_model, user_q)
        if err: st.error(err); st.stop()
    st.session_state.chat_history.append({"role":"user","text":user_q,"time":datetime.utcnow().isoformat()})
    st.session_state.chat_history.append({"role":"assistant","text":answer_text,"time":datetime.utcnow().isoformat()})
    st.markdown(f"### 📘 Lời giải\n{answer_text}")
    if tts_enabled: speak_text(answer_text)

    # Sinh ảnh tự động
    img_prompt = f"Educational illustration with style '{style}': {user_q}."
    with st.spinner("🎨 Đang sinh ảnh minh họa..."):
        img_b64, img_err = call_gemini_image(st.session_state.chosen_model, img_prompt)
    if img_err:
        st.warning("Không tạo được ảnh: " + img_err)
    else:
        store_image_entry(user_q, img_b64, style)
        st.image(base64.b64decode(img_b64), use_column_width=True)
        st.download_button("📥 Tải ảnh minh họa", data=base64.b64decode(img_b64), file_name="minh_hoa.png", mime="image/png")
        st.session_state.chat_history[-1]["image"] = base64.b64decode(img_b64)
