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
    "Bạn là Gia sư ảo thân thiện và kiên nhẫn. "
    "Hãy giải bài cho học sinh cấp 2–3, trình bày dễ hiểu, dùng LaTeX cho công thức."
)

# ==========================
# 🖼️ BASE64 IMAGE
# ==========================

def get_base64_image(image_file):
    if image_file is None:
        return None
    return base64.b64encode(image_file.getvalue()).decode("utf-8")

# ==========================
# 🤖 API CALL
# ==========================

def get_gemini_response(prompt: str, image_data: str = None):
    history = st.session_state.get("chat_history", [])[:-1]

    history_contents = []
    for msg in history:
        if not msg.get("content"):
            continue
        history_contents.append({
            "role": msg["role"],
            "parts": [{"text": msg["content"]}]
        })

    current_parts = []
    uploaded_file = st.session_state.get("uploaded_file")

    if image_data and uploaded_file:
        mime = getattr(uploaded_file, "type", "image/jpeg")
        current_parts.append({
            "inlineData": {"mimeType": mime, "data": image_data}
        })

    if prompt:
        current_parts.append({"text": prompt})
    if not current_parts:
        current_parts.append({"text": ""})

    payload = {
        "contents": history_contents + [{
            "role": "user",
            "parts": current_parts
        }],
        "systemInstruction": {"role": "system", "parts": [{"text": SYSTEM_INSTRUCTION}]}
    }

    res = requests.post(
        API_URL,
        headers={"Content-Type": "application/json"},
        json=payload
    )

    if res.status_code == 200:
        data = res.json()
        text = (
            data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", None)
        )
        return text or "Không tìm thấy nội dung trả lời."

    if res.status_code in (401, 403):
        return f"❌ API KEY không hợp lệ hoặc không có quyền truy cập (mã {res.status_code})."

    return f"❌ Lỗi API: mã {res.status_code}"

# ==========================
# 💾 SESSION STATE
# ==========================

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "user_info" not in st.session_state:
    st.session_state["user_info"] = {}

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "uploaded_file" not in st.session_state:
    st.session_state["uploaded_file"] = None

# Flag reset input sau khi gửi
if "should_reset_input" not in st.session_state:
    st.session_state["should_reset_input"] = False

# ==========================
# 🧹 RESET INPUT SAU RERUN
# ==========================

if st.session_state["should_reset_input"]:
    st.session_state["user_input"] = ""
    st.session_state["uploaded_file"] = None
    st.session_state["should_reset_input"] = False


# ==========================
# 🔑 LOGIN
# ==========================

def handle_login(name, class_name):
    if not name or not class_name:
        st.error("⚠️ Vui lòng nhập đầy đủ thông tin.")
        return

    st.session_state["user_info"] = {"name": name, "class": class_name}
    st.session_state["logged_in"] = True
    st.session_state["chat_history"] = [
        {"role": "assistant", "content": f"Chào {name} (Lớp {class_name})! Tôi là Gia sư ảo của bạn."}
    ]

    st.experimental_rerun()

# ==========================
# 💬 SUBMIT MESSAGE
# ==========================

def submit_chat():
    text = st.session_state.get("user_input", "").strip()
    file = st.session_state.get("uploaded_file")

    if not text and not file:
        return

    image_base64 = None
    if file:
        image_base64 = get_base64_image(file)
        st.session_state["chat_history"].append({
            "role": "user",
            "content": f"Hình ảnh: {file.name}",
            "image": file
        })

    if text:
        st.session_state["chat_history"].append({
            "role": "user",
            "content": text
        })

    with st.spinner("⏳ Đang suy nghĩ..."):
        reply = get_gemini_response(text, image_base64)

    st.session_state["chat_history"].append({
        "role": "assistant",
        "content": reply
    })

    # 👉 KHÔNG reset input ở đây — đưa về flag
    st.session_state["should_reset_input"] = True


# ==========================
# 💻 UI
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
    user = st.session_state["user_info"]

    st.subheader(f"Xin chào, {user['name']} (Lớp {user['class']}) ✨")
    st.markdown("---")

    if st.button("Đăng xuất"):
        st.session_state["logged_in"] = False
        st.session_state["chat_history"] = []
        st.experimental_rerun()

    chat_container = st.container()
    with chat_container:
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                if "image" in msg:
                    st.image(msg["image"], caption=msg["content"], width=250)
                else:
                    st.write(msg["content"])

    st.file_uploader("Tải ảnh bài tập (tùy chọn)", type=["png", "jpg", "jpeg"], key="uploaded_file")

    with st.form("chat_form", clear_on_submit=True):
        st.text_input("Nhập câu hỏi", key="user_input")
        if st.form_submit_button("Gửi"):
            submit_chat()


if not st.session_state["logged_in"]:
    show_login()
else:
    show_chat()
