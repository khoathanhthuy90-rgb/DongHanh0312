import streamlit as st
import requests
import base64
import io
from PIL import Image
import time

# =============================================
# CẤU HÌNH GEMINI
# =============================================
GEMINI_MODEL = "gemini-2.0-flash"
API_KEY = st.secrets["GEMINI_API_KEY"]
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"

# =============================================
# SYSTEM PROMPT
# =============================================
SYSTEM_INSTRUCTION = """
Bạn là trợ lý AI chuyên giải bài tập, giải thích rõ ràng và chi tiết.
"""

# =============================================
# STYLE CSS – UI ĐẸP
# =============================================
CHAT_CSS = """
<style>

html, body, [class*="css"] {
    font-family: "Segoe UI", sans-serif;
}

.chat-container {
    padding: 12px 20px;
    border-radius: 12px;
    margin: 10px 0;
    max-width: 85%;
}

.user-msg {
    background: #DCF7C5;
    margin-left: auto;
    border: 1px solid #b7e3a2;
}

.bot-msg {
    background: #F1F0F0;
    border: 1px solid #dcdcdc;
}

.msg-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
}

.input-box {
    position: fixed;
    bottom: 0;
    left: 0;
    padding: 12px;
    background: white;
    width: 100%;
    border-top: 1px solid #e0e0e0;
}

.stTextInput>div>div>input {
    border-radius: 8px;
}

.preview-img {
    border-radius: 8px;
    margin-top: 6px;
    border: 1px solid #ddd;
}
</style>
"""

st.markdown(CHAT_CSS, unsafe_allow_html=True)

# =============================================
# XỬ LÝ ẢNH
# =============================================
def img_to_base64(uploaded_file):
    if uploaded_file is None:
        return None
    image = Image.open(uploaded_file)
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# =============================================
# GỬI REQUEST GEMINI
# =============================================
def get_gemini_response(prompt, image_data=None):
    chat_history = st.session_state.get("chat_history", [])

    history_contents = []
    for msg in chat_history:
        if msg["role"] == "system":
            continue
        history_contents.append({
            "role": msg["role"],
            "parts": [{"text": msg["content"]}]
        })

    parts = []

    uploaded_file_obj = st.session_state.get("uploaded_file", None)
    if image_data and uploaded_file_obj:
        mime = getattr(uploaded_file_obj, "type", "image/jpeg")
        parts.append({
            "inlineData": {"mimeType": mime, "data": image_data}
        })

    parts.append({"text": prompt})

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": SYSTEM_INSTRUCTION}]}
        ] + history_contents + [
            {"role": "user", "parts": parts}
        ]
    }

    res = requests.post(
        API_URL, headers={"Content-Type": "application/json"},
        json=payload, timeout=45
    )

    if res.status_code != 200:
        return f"❌ Lỗi API {res.status_code}: {res.text}"

    data = res.json()
    return (
        data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
    )

# =============================================
# HIỂN THỊ TIN NHẮN
# =============================================
def render_chat():
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(
                f"""
                <div class="chat-container user-msg">
                    <b>🧑 Bạn:</b><br>{msg['content']}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div class="chat-container bot-msg">
                    <b>🤖 AI:</b><br>{msg['content']}
                </div>
                """,
                unsafe_allow_html=True
            )


# =============================================
# GIAO DIỆN CHÍNH
# =============================================
def show_chat():
    st.title("📘 Chatbot Giải Bài Tập – Gemini AI")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Upload ảnh
    uploaded_file = st.file_uploader(
        "📷 Tải ảnh bài tập (tùy chọn)",
        type=["jpg", "jpeg", "png"],
        key="upload_image"
    )
    st.session_state.uploaded_file = uploaded_file

    if uploaded_file:
        st.image(uploaded_file, caption="Ảnh bạn đã chọn", use_column_width=True)

    st.markdown("---")

    # Hiển thị chat history
    render_chat()

    # INPUT FIXED DƯỚI
    with st.container():
        st.markdown('<div class="input-box">', unsafe_allow_html=True)

        cols = st.columns([4, 1])
        with cols[0]:
            user_input = st.text_input("Nhập câu hỏi:", key="text_box", label_visibility="collapsed")
        with cols[1]:
            send_btn = st.button("Gửi", use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Xử lý gửi tin
    if send_btn:
        if not user_input and not uploaded_file:
            st.warning("Bạn cần nhập nội dung hoặc tải ảnh lên.")
            st.stop()

        st.session_state.chat_history.append({"role": "user", "content": user_input})

        base64_img = img_to_base64(uploaded_file)
        bot_reply = get_gemini_response(user_input, base64_img)

        st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})

        time.sleep(0.1)
        st.experimental_rerun()


# =============================================
# RUN APP
# =============================================
if __name__ == "__main__":
    show_chat()
