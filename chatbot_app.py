# app.py (ENHANCED)
import streamlit as st
import requests
import base64
import uuid
from datetime import datetime
import io

# --------------------------
# CONFIG
# --------------------------
# Put your Gemini key into .streamlit/secrets.toml as:
# GEMINI_API_KEY = "-----"
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = None

if not API_KEY:
    st.error("⚠️ Thiếu GEMINI_API_KEY trong .streamlit/secrets.toml")
    st.stop()

# Default model (can be changed in sidebar)
MODEL_OPTIONS = {
    "Gemini 2.0 Flash (nhanh)": "gemini-2.0-flash",
    "Gemini 2.0 Pro (mạnh)": "gemini-2.0-pro-exp",
    "Gemini 1.5 Flash": "gemini-1.5-flash"
}

SYSTEM_INSTRUCTION = (
    "Bạn là gia sư ảo thân thiện, giải bài cho học sinh cấp 2–3. "
    "Trình bày rõ ràng, dùng LaTeX cho công thức khi cần. Nếu có ảnh, sử dụng ảnh để giải thích."
)

# --------------------------
# SESSION INIT
# --------------------------
st.set_page_config(page_title="Gia Sư Ảo – Minh họa & TTS", layout="wide", page_icon="🤖")
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # list of dicts: {"role","text","time","image"(opt)}
if "image_history" not in st.session_state:
    st.session_state.image_history = []  # list of dicts: {"id","question","b64","style","time"}
if "chosen_model" not in st.session_state:
    st.session_state.chosen_model = list(MODEL_OPTIONS.values())[0]
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# --------------------------
# STYLE PROMPTS
# --------------------------
STYLE_PROMPT_MAP = {
    "Sơ đồ toán học (diagram)": "diagram-style, clear labels, vector lines, simple shapes, white background, black axis lines",
    "Minh họa đơn giản (simple illustration)": "flat simple illustration, clean colors, educational style, minimal text, clear shapes",
    "Tranh hoạt hình (cartoon)": "cartoon style, friendly characters, colorful, playful, simplified shapes",
    "Phong cách sách giáo khoa (textbook style)": "textbook illustration, clear labeled parts, muted colors, high clarity",
    "Ảnh thật (realistic)": "photo-realistic, realistic lighting, natural textures, high resolution"
}

# --------------------------
# HELPERS: Gemini endpoints
# --------------------------
def text_api_url(model):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"

# --------------------------
# CALL GEMINI TEXT (generateContent)
# --------------------------
def call_gemini_text(model, user_prompt, image_b64_inline=None):
    url = text_api_url(model)
    # Build contents: system + user parts (optionally inline image)
    contents = [
        {"role": "user", "parts": [{"text": SYSTEM_INSTRUCTION}]}
    ]

    parts = []
    if image_b64_inline:
        # include inline image in request so model can reference it
        parts.append({"inlineData": {"mimeType": "image/png", "data": image_b64_inline}})
    parts.append({"text": user_prompt})
    contents.append({"role": "user", "parts": parts})

    payload = {"contents": contents}

    try:
        res = requests.post(url, json=payload, timeout=45)
    except Exception as e:
        return None, f"Lỗi kết nối API (text): {e}"

    if res.status_code != 200:
        return None, f"API text trả lỗi {res.status_code}: {res.text[:300]}"

    try:
        data = res.json()
    except Exception as e:
        return None, f"Lỗi decode JSON (text): {e}. Raw: {res.text[:200]}"

    # Extract text
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text, None
    except Exception as e:
        return None, f"Lỗi đọc phản hồi từ API: {e}"

# --------------------------
# CALL GEMINI IMAGE (via generateContent -> media)
# --------------------------
def call_gemini_image(model, prompt):
    url = text_api_url(model)
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    try:
        res = requests.post(url, json=payload, timeout=90)
    except Exception as e:
        return None, f"Lỗi kết nối API (image): {e}"

    if res.status_code != 200:
        return None, f"API image trả lỗi {res.status_code}: {res.text[:300]}"

    try:
        data = res.json()
    except Exception as e:
        return None, f"Lỗi decode JSON (image): {e}. Raw start: {res.text[:300]}"

    # Look for media in parts
    try:
        parts = data["candidates"][0]["content"]["parts"]
        for p in parts:
            if "media" in p and isinstance(p["media"], dict):
                # media.data is base64 bytes for image/png
                return p["media"]["data"], None
        return None, "Không tìm thấy trường media trong phản hồi."
    except Exception as e:
        return None, f"Lỗi đọc media từ response: {e}"

# --------------------------
# TEXT-TO-SPEECH (gTTS)
# --------------------------
def speak_text(text):
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="vi")
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp.read(), format="audio/mp3")
    except Exception as e:
        st.warning("Không thể tạo giọng nói (gTTS). Lỗi: " + str(e))

# --------------------------
# UI: SIDEBAR CONTROLS
# --------------------------
with st.sidebar:
    st.title("⚙️ Cài đặt")
    chosen_label = st.selectbox("Chọn model Gemini", list(MODEL_OPTIONS.keys()))
    st.session_state.chosen_model = MODEL_OPTIONS[chosen_label]
    st.markdown("---")
    st.subheader("Ảnh minh họa")
    style = st.selectbox("Phong cách ảnh", list(STYLE_PROMPT_MAP.keys()))
    extra = st.text_input("Ghi chú thêm cho ảnh (tùy chọn)", placeholder="ví dụ: 'no text, white background'")
    st.markdown("---")
    st.subheader("Tính năng")
    tts_enabled = st.checkbox("Bật Text-to-Speech (gTTS)", value=False)
    st.markdown("Phiên bản app: enhanced with image + TTS + history")

# --------------------------
# QUICK SUGGESTIONS (small buttons)
# --------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("Gợi ý nhanh")
if st.sidebar.button("Giải định lý Py-ta-go"):
    st.session_state.user_input = "Hãy giải và minh họa định lý Pythagore bằng ví dụ tam giác vuông."
if st.sidebar.button("Ví dụ bài toán thực tế"):
    st.session_state.user_input = "Một cây cao có bóng dài 5m. Một cây khác cao 3m có bóng 2m. Hỏi chiều cao cây kia là bao nhiêu?"

# --------------------------
# MAIN UI
# --------------------------
st.markdown("<h1 style='text-align:center'>👨‍🏫 Gia Sư Ảo – Minh họa & Thuyết trình</h1>", unsafe_allow_html=True)
col_left, col_right = st.columns([3,2])

with col_left:
    st.subheader("Nhập đề bài / câu hỏi")
    user_q = st.text_area("Nhập đề bài hoặc câu hỏi:", value=st.session_state.get("user_input",""), height=160)
    st.session_state.user_input = user_q

    row1, row2 = st.columns([1,1])
    with row1:
        btn_send = st.button("Gửi & Sinh ảnh")
    with row2:
        btn_only_image = st.button("Chỉ sinh ảnh minh họa")

with col_right:
    st.subheader("Nhật ký nhanh")
    st.markdown("- Lịch sử lời giải và ảnh sẽ lưu trong phiên này.")
    st.markdown("- Tải ảnh để chèn slide hoặc nộp báo cáo.")
    if st.button("Đọc trả lời cuối (TTS)") and tts_enabled:
        # find last assistant text
        for msg in reversed(st.session_state.chat_history):
            if msg["role"] == "assistant" and msg.get("text"):
                speak_text(msg["text"])
                break

# --------------------------
# ACTION: Only Image
# --------------------------
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

if btn_only_image and user_q.strip():
    # build image prompt
    style_desc = STYLE_PROMPT_MAP.get(style, "")
    img_prompt = f"Create an educational, {style} illustration. {style_desc}. Illustrate the following problem clearly for middle school students: {user_q}."
    if extra:
        img_prompt += " Additional instructions: " + extra

    with st.spinner("🎨 AI đang sinh ảnh minh họa — vui lòng chờ (có thể 10–30s)..."):
        img_b64, img_err = call_gemini_image(st.session_state.chosen_model, img_prompt)

    if img_err:
        st.error("❌ Lỗi khi sinh ảnh: " + img_err)
    else:
        # store and show
        store_image_entry(user_q, img_b64, style)
        st.success("✅ Ảnh minh họa đã tạo xong.")
        st.image(base64.b64decode(img_b64), use_column_width=True)
        st.download_button("📥 Tải ảnh minh họa", data=base64.b64decode(img_b64), file_name="minh_hoa.png", mime="image/png")

# --------------------------
# ACTION: Send & Image
# --------------------------
if btn_send and user_q.strip():
    # 1) Call text
    with st.spinner("⏳ Đang tạo lời giải (AI)..."):
        answer_text, err = call_gemini_text(st.session_state.chosen_model, user_q)
    if err:
        st.error(err)
    else:
        # append to history
        st.session_state.chat_history.append({"role": "user", "text": user_q, "time": datetime.utcnow().isoformat()})
        st.session_state.chat_history.append({"role": "assistant", "text": answer_text, "time": datetime.utcnow().isoformat()})

        # show text immediately
        st.markdown("### 📘 Lời giải")
        st.markdown(answer_text)

        # optional TTS
        if tts_enabled:
            with st.spinner("🔊 Đang tạo giọng nói..."):
                speak_text(answer_text)

        # 2) create image
        style_desc = STYLE_PROMPT_MAP.get(style, "")
        img_prompt = f"Create an educational, {style} illustration. {style_desc}. Illustrate the following problem clearly for middle school students: {user_q}."
        if extra:
            img_prompt += " Additional instructions: " + extra

        with st.spinner("🎨 AI đang sinh ảnh minh họa..."):
            img_b64, img_err = call_gemini_image(st.session_state.chosen_model, img_prompt)

        if img_err:
            st.warning("Không tạo được ảnh: " + img_err)
        else:
            # store and attach to the assistant message
            store_image_entry(user_q, img_b64, style)
            st.image(base64.b64decode(img_b64), use_column_width=True)
            st.download_button("📥 Tải ảnh minh họa", data=base64.b64decode(img_b64), file_name="minh_hoa.png", mime="image/png")
            # also attach b64 to last assistant message for history view
            st.session_state.chat_history[-1]["image"] = base64.b64decode(img_b64)

# --------------------------
# SHOW HISTORY (chat + images)
# --------------------------
st.markdown("---")
left_col, right_col = st.columns([3,1])
with left_col:
    st.header("💬 Lịch sử trò chuyện")
    if not st.session_state.chat_history:
        st.info("Chưa có lời giải nào. Nhập đề bài và bấm 'Gửi & Sinh ảnh'.")
    else:
        for m in st.session_state.chat_history[-12:]:
            if m["role"] == "user":
                st.markdown(f"<div style='text-align:right'><b>🧑‍🎓 Bạn:</b> {m['text']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:left'><b>🤖 Gia sư ảo:</b> {m['text']}</div>", unsafe_allow_html=True)
                if m.get("image"):
                    st.image(m["image"], use_column_width=True)

with right_col:
    st.header("📂 Nhật ký ảnh")
    if not st.session_state.image_history:
        st.info("Chưa có ảnh minh họa nào.")
    else:
        # show latest 6
        for entry in reversed(st.session_state.image_history[-12:]):
            st.image(base64.b64decode(entry["b64"]), width=160)
            st.write(f"📝 {entry['question'][:80]}{'...' if len(entry['question'])>80 else ''}")
            st.write(f"- Phong cách: {entry['style']}")
            st.write(f"- Thời gian: {entry['time']}")
            st.download_button("Tải ảnh", data=base64.b64decode(entry["b64"]), file_name=f"minh_hoa_{entry['id']}.png", mime="image/png")
            st.markdown("---")

# --------------------------
# FOOTER
# --------------------------
st.markdown("---")
st.caption("Ghi chú: Kiểm tra quyền sử dụng ảnh nếu sử dụng cho mục đích thương mại. Ứng dụng sử dụng API Gemini (Google).")
