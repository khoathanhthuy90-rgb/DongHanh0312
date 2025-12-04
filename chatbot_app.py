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

# ==========================
# ❗❗ SỬA LỖI 403 Ở ĐÂY
# ==========================
API_URL = (
    f"https://generativelanguage.googleapis.com/v1/models/"
    f"{GEMINI_MODEL}:generateContent?key={API_KEY}"
)
# ==========================

SYSTEM_INSTRUCTION = (
    "Bạn là Gia sư ảo thân thiện và kiên nhẫn. "
    "Hãy giải bài cho học sinh cấp 2–3, trình bày dễ hiểu, dùng LaTeX cho công thức."
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
    chat_history = st.session_state.get("chat_history", [])
    history_for_api = chat_history[:-1] if len(chat_history) > 0 else []

    history_contents = []
    for msg in history_for_api:
        if not msg.get("content"):
            continue
        history_contents.append({
            "role": msg.get("role", "user"),
            "parts": [{"text": msg["content"]}]
        })

    current_parts = []
    uploaded_file_obj = st.session_state.get("uploaded_file")

    if image_data and uploaded_file_obj:
        mime = getattr(uploaded_file_obj, "type", "image/jpeg")
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

    try:
        res = requests.post(
            API_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
    except requests.RequestException as e:
        return f"❌ Lỗi kết nối API: {e}"

    if res.status_code == 200:
        try:
            data = res.json()
            text = (
                data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", None)
            )
            return text or "Không nhận được phản hồi từ model."
        except Exception:
            return "Không thể phân tích phản hồi từ server."
    elif res.status_code in (401, 403):
        return f"❌ Lỗi xác thực (mã {res.status_code}). Kiểm tra API_KEY và quyền model."
    else:
        return f"❌ Lỗi API: mã {res.status_code}. Nội dung: {res.text[:300]}"

# ==========================
# 💾 KHỞI TẠO SESSION STATE
# ==========================
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user_info", {})
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("uploaded_file_widget", None)
st.session_state.setdefault("uploaded_file", None)
st.session_state.setdefault("user_input", "")
st.session_state.setdefault("should_reset_input", False)

if st.session_state.get("should_reset_input", False):
    st.session_state["user_input"] = ""
    st.session_state["uploaded_file"] = None
    st.session_state["should_reset_input"] = False

# ==========================
# 🔑 ĐĂNG NHẬP
# ==========================
def handle_login(name, class_name):
    if not name or not class_name:
        st.error("⚠️ Vui lòng nhập đầy đủ thông tin.")
        return
    st.session_state["user_info"] = {"name": name, "class": class_name}
    st.session_state["logged_in"] = True
    st.session_state["chat_history"] = [
        {"role": "assistant", "content": f"Chào bạn, **{name} (Lớp {class_name})**! Tôi là Gia sư ảo."}
    ]

# ==========================
# 💬 GỬI TIN NHẮN
# ==========================
def submit_chat():
    text = st.session_state.get("user_input", "").strip()
    widget_file = st.session_state.get("uploaded_file_widget")

    if not text and not widget_file:
        return

    image_base64 = None
    if widget_file:
        try:
            image_base64 = get_base64_image(widget_file)
            st.session_state["uploaded_file"] = widget_file
            st.session_state["chat_history"].append({
                "role": "user",
                "content": f"📷 Hình ảnh: {getattr(widget_file, 'name', 'uploaded_image')}",
                "image": widget_file
            })
        except Exception as e:
            st.error(f"Lỗi xử lý hình ảnh: {e}")
            return

    if text:
        st.session_state["chat_history"].append({"role": "user", "content": text})

    with st.spinner("⏳ Gia sư đang phân tích..."):
        reply = get_gemini_response(text, image_base64)

    st.session_state["chat_history"].append({"role": "assistant", "content": reply})
    st.session_state["should_reset_input"] = True

# ==========================
# 💻 GIAO DIỆN
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
    user = st.session_state.get("user_info", {"name": "Học sinh", "class": ""})
    st.subheader(f"Xin chào, {user.get('name')} (Lớp {user.get('class')}) ✨")
    st.markdown("---")

    if st.button("Đăng xuất"):
        st.session_state["logged_in"] = False
        st.session_state["chat_history"] = []
        return

    for msg in st.session_state.get("chat_history", []):
        with st.chat_message(msg.get("role", "user")):
            if "image" in msg:
                try:
                    st.image(msg["image"], caption=msg.get("content", ""), width=220)
                except Exception:
                    st.write(msg.get("content", ""))
            else:
                st.write(msg.get("content", ""))

    st.file_uploader(
        "Tải ảnh bài tập (tùy chọn)",
        type=["png", "jpg", "jpeg"],
        key="uploaded_file_widget",
        accept_multiple_files=False
    )

    with st.form("chat_form", clear_on_submit=True):
        st.text_input("Nhập câu hỏi", key="user_input", placeholder="Ví dụ: Giải phương trình...")
        if st.form_submit_button("Gửi"):
            submit_chat()

# ==========================
# 🚀 RUN
# ==========================
if not st.session_state.get("logged_in", False):
    show_login()
else:
    show_chat()
