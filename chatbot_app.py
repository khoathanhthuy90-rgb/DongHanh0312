import streamlit as st
import requests
import time
import json
import base64
from io import BytesIO

# ==========================
# ⚙️ CẤU HÌNH API GEMINI
# ==========================

GEMINI_MODEL = "gemini-2.0-flash"
API_KEY = st.secrets["GEMINI_API_KEY"]
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"

SYSTEM_INSTRUCTION = (
    "Bạn là Gia sư ảo thân thiện và kiên nhẫn. Nhiệm vụ của bạn là giải đáp các câu hỏi "
    "về các môn học cho học sinh cấp 2 và cấp 3. Hãy: "
    "1. Đưa ra câu trả lời chi tiết, dễ hiểu, sử dụng **LaTeX** cho tất cả công thức toán học và phương trình hóa học. "
    "2. Nếu có hình ảnh, hãy phân tích hình ảnh trước khi trả lời. "
    "3. Giữ giọng điệu chuyên nghiệp nhưng khuyến khích học sinh đặt thêm câu hỏi."
)

# ==========================
# 🖼️ CHUYỂN ĐỔI HÌNH ẢNH BASE64
# ==========================

def get_base64_image(image_file):
    if image_file is None:
        return None
    return base64.b64encode(image_file.getvalue()).decode("utf-8")

# ==========================
# 🤖 HÀM GỌI API GEMINI
# ==========================

def get_gemini_response(prompt: str, image_data: str = None):
    uploaded_file_info = st.session_state.uploaded_file

    history_contents = []
    chat_history_for_api = st.session_state.chat_history[:-1]

    for message in chat_history_for_api:
        parts = []
        if "content" in message:
            parts.append({"text": message["content"]})
        if parts:
            history_contents.append({"role": message["role"], "parts": parts})

    current_parts = []
    if image_data and uploaded_file_info:
        current_parts.append({
            "inlineData": {
                "mimeType": uploaded_file_info.type,
                "data": image_data
            }
        })

    if prompt:
        current_parts.append({"text": prompt})

    payload = {
        "contents": history_contents + [{"role": "user", "parts": current_parts}],
        "systemInstruction": {"role": "system", "parts": [{"text": SYSTEM_INSTRUCTION}]}
    }

    max_retries = 3
    last_code = None

    for attempt in range(max_retries):
        try:
            res = requests.post(
                API_URL,
                headers={"Content-Type": "application/json"},
                json=payload
            )

            if res.status_code == 200:
                data = res.json()
                return (
                    data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "Xin lỗi, tôi không tìm thấy câu trả lời.")
                )

            last_code = res.status_code
            st.warning(f"Thử lại lần {attempt + 1}/{max_retries} thất bại. Mã: {last_code}")
            time.sleep(1.2 * (attempt + 1))

        except Exception as e:
            return f"❌ Lỗi kết nối API: {e}"

    st.error(f"❌ Lỗi API nghiêm trọng: {last_code}")
    return "Xin lỗi, hệ thống đang gặp sự cố."

# ==========================
# 💾 QUẢN LÝ SESSION STATE
# ==========================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_info" not in st.session_state:
    st.session_state.user_info = {}

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

# ==========================
# 🔑 ĐĂNG NHẬP
# ==========================

def handle_login(name, class_name):
    if not name or not class_name:
        st.error("⚠️ Vui lòng nhập đầy đủ thông tin.")
        return

    st.session_state.user_info = {"name": name, "class": class_name}
    st.session_state.logged_in = True

    st.session_state.chat_history = [
        {"role": "assistant", "content": f"Chào bạn, **{name} (Lớp {class_name})**! Tôi là Gia sư ảo của bạn."}
    ]

    st.rerun()

# ==========================
# 💬 GỬI TIN NHẮN
# ==========================

def submit_chat():
    text = st.session_state.user_input.strip()
    uploaded_file = st.session_state.uploaded_file

    if not text and not uploaded_file:
        return

    image_base64 = None
    if uploaded_file:
        try:
            image_base64 = get_base64_image(uploaded_file)
            st.session_state.chat_history.append({"role": "user", "content": f"Hình ảnh: {uploaded_file.name}", "image": uploaded_file})
        except Exception as e:
            st.error(f"Lỗi hình ảnh: {e}")
            return

    if text:
        st.session_state.chat_history.append({"role": "user", "content": text})

    with st.spinner("⏳ Đang suy nghĩ..."):
        reply = get_gemini_response(text, image_base64)

    st.session_state.chat_history.append({"role": "assistant", "content": reply})

    st.session_state.uploaded_file = None
    st.rerun()

# ==========================
# 💻 GIAO DIỆN CHÍNH
# ==========================

st.set_page_config(page_title="Gia sư ảo", layout="centered")
st.title("👨‍🏫 Gia Sư Ảo — Đề Tài Nghiên Cứu Khoa Học")
st.markdown("---")


def show_login():
    st.subheader("Đăng nhập để bắt đầu học")
    with st.form("login_form"):
        name = st.text_input("Họ và tên")
        class_name = st.text_input("Lớp học")
        if st.form_submit_button("Bắt đầu"):
            handle_login(name, class_name)


def show_chat():
    user = st.session_state.user_info
    st.subheader(f"Xin chào, {user['name']} (Lớp {user['class']}) ✨")
    st.markdown("---")

    if st.button("Đăng xuất", type="primary"):
        st.session_state.logged_in = False
        st.session_state.chat_history = []
        st.rerun()

    chat_container = st.container(height=400, border=True)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                if "image" in msg:
                    st.image(msg["image"], caption=msg["content"], width=220)
                else:
                    st.write(msg["content"])

    st.file_uploader("Tải ảnh bài tập (tùy chọn)", type=["png", "jpg", "jpeg"], key="uploaded_file")

    with st.form("chat_form", clear_on_submit=True):
        st.text_input("Nhập câu hỏi", key="user_input", placeholder="Ví dụ: Giải phương trình...")
        if st.form_submit_button("Gửi", type="primary"):
            submit_chat()


if not st.session_state.logged_in:
    show_login()
else:
    show_chat()
