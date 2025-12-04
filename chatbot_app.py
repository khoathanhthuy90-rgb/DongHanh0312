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

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = None

if not API_KEY:
    st.error("⚠️ Vui lòng thêm GEMINI_API_KEY vào .streamlit/secrets.toml")
    st.stop()

API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={API_KEY}"
)

SYSTEM_INSTRUCTION = (
    "Bạn là Gia sư ảo thân thiện. Giải thích rõ ràng, dùng LaTeX cho toàn bộ công thức."
)

# ==========================
# 🖼️ BASE64 IMAGE
# ==========================

def get_base64_image(image_file):
    if image_file is None:
        return None
    return base64.b64encode(image_file.getvalue()).decode("utf-8")

# ==========================
# 🤖 GỌI API GEMINI
# ==========================

def get_gemini_response(prompt: str, image_data: str = None):
    uploaded_file_info = st.session_state.get("uploaded_file")

    history_contents = []
    chat_history = st.session_state.get("chat_history", [])
    chat_history_for_api = chat_history[:-1] if len(chat_history) > 0 else []

    for message in chat_history_for_api:
        parts = []
        if "content" in message and message["content"]:
            parts.append({"text": message["content"]})
        history_contents.append({"role": message["role"], "parts": parts})

    current_parts = []

    if image_data and uploaded_file_info:
        mime = getattr(uploaded_file_info, "type", "image/jpeg")
        current_parts.append({
            "inlineData": {
                "mimeType": mime,
                "data": image_data
            }
        })

    if prompt:
        current_parts.append({"text": prompt})
    if not current_parts:
        current_parts.append({"text": ""})

    payload = {
        "contents": history_contents + [{"role": "user", "parts": current_parts}],
        "systemInstruction": {
            "role": "system",
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        }
    }

    try:
        res = requests.post(API_URL, headers={"Content-Type": "application/json"}, json=payload)

        if res.status_code == 200:
            data = res.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            return text or "Không nhận được phản hồi từ model."

        return f"❌ Lỗi API: mã {res.status_code}"

    except Exception as e:
        return f"❌ Lỗi kết nối API: {e}"

# ==========================
# 💾 SESSION STATE
# ==========================

st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user_info", {})
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("uploaded_file", None)
st.session_state.setdefault("user_input", "")

# ==========================
# 🔑 ĐĂNG NHẬP
# ==========================

def handle_login(name, class_name):
    if not name or not class_name:
        st.error("⚠️ Vui lòng nhập đầy đủ.")
        return

    st.session_state["user_info"] = {"name": name, "class": class_name}
    st.session_state["logged_in"] = True
    st.session_state["chat_history"] = [{
        "role": "assistant",
        "content": f"Chào bạn **{name} (Lớp {class_name})**! Tôi là Gia sư ảo của bạn."
    }]

# ==========================
# 💬 GỬI TIN NHẮN
# ==========================

def submit_chat():
    text = st.session_state.get("user_input", "").strip()
    uploaded_file = st.session_state.get("uploaded_file")

    if not text and not uploaded_file:
        return

    image_base64 = None
    if uploaded_file:
        image_base64 = get_base64_image(uploaded_file)
        st.session_state["chat_history"].append({
            "role": "user",
            "content": f"📷 Hình ảnh: {uploaded_file.name}",
            "image": uploaded_file
        })

    if text:
        st.session_state["chat_history"].append(
            {"role": "user", "content": text}
        )

    with st.spinner("⏳ Đang suy nghĩ..."):
        reply = get_gemini_response(text, image_base64)

    st.session_state["chat_history"].append({
        "role": "assistant",
        "content": reply
    })

    # Reset input
    st.session_state["user_input"] = ""
    st.session_state["uploaded_file"] = None

# ==========================
# 💻 GIAO DIỆN
# ==========================

st.set_page_config(page_title="Gia sư ảo")

st.title("👨‍🏫 Gia Sư Ảo — Đề tài Nghiên cứu Khoa học")
st.markdown("---")

def show_login():
    st.subheader("Đăng nhập để bắt đầu")
    with st.form("login_form"):
        name = st.text_input("Họ và tên")
        class_name = st.text_input("Lớp học")
        if st.form_submit_button("Bắt đầu"):
            handle_login(name, class_name)

def show_chat():
    user = st.session_state["user_info"]
    st.subheader(f"Xin chào, {user['name']} (Lớp {user['class']}) ✨")
    st.markdown("---")

    if st.button("Đăng xuất"):
        st.session_state["logged_in"] = False
        st.session_state["chat_history"] = []
        return

    # HIỆN LỊCH SỬ CHAT
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            if "image" in msg:
                st.image(msg["image"], caption=msg["content"], width=240)
            else:
                st.write(msg["content"])

    st.file_uploader("Tải ảnh bài tập", type=["png", "jpg", "jpeg"], key="uploaded_file")

    with st.form("chat_form"):
        st.text_input("Nhập câu hỏi", key="user_input")
        if st.form_submit_button("Gửi"):
            submit_chat()

# ==========================
# 🚀 START
# ==========================

if not st.session_state["logged_in"]:
    show_login()
else:
    show_chat()
