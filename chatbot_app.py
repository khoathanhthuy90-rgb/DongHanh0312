import streamlit as st
import requests
import time
import json

# ==========================
#   CẤU HÌNH API GEMINI
# ==========================

GEMINI_MODEL = "gemini-1.5-flash"

API_KEY = st.secrets.get("API_KEY", None)

if not API_KEY:
    st.error("❌ Thiếu API_KEY trong secrets! Vui lòng thêm API_KEY vào .streamlit/secrets.toml")
    st.stop()

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

SYSTEM_INSTRUCTION = (
    "Bạn là Gia sư ảo thân thiện và kiên nhẫn. "
    "Hãy giải thích kiến thức các môn học thật dễ hiểu cho học sinh cấp 2 và cấp 3."
)

# ==========================
#   HÀM GỌI API GEMINI
# ==========================

def get_gemini_response(prompt: str):
    payload = {
        "system_instruction": {"role": "system", "parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }

    max_retries = 3
    last_code = None

    for attempt in range(max_retries):
        try:
            res = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload))

            if res.status_code == 200:
                data = res.json()
                return (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "Xin lỗi, tôi không tìm thấy câu trả lời.")
                )

            last_code = res.status_code
            time.sleep(1.5 * (attempt + 1))

        except Exception as e:
            return f"❌ Lỗi kết nối API: {e}"

    return f"❌ Lỗi API (mã {last_code}). Vui lòng thử lại sau."

# ==========================
#   QUẢN LÝ SESSION STATE
# ==========================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_info" not in st.session_state:
    st.session_state.user_info = {}

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ==========================
#   ĐĂNG NHẬP
# ==========================

def handle_login(name, class_name):
    if not name or not class_name:
        st.error("⚠️ Vui lòng nhập đầy đủ thông tin.")
        return

    st.session_state.user_info = {"name": name, "class": class_name}
    st.session_state.logged_in = True

    st.session_state.chat_history = [
        {"role": "assistant", "content": f"Chào {name} (Lớp {class_name}) 👋. Bạn muốn hỏi gì về Toán – Lý – Hóa?"}
    ]

    st.rerun()


# ==========================
#   GỬI TIN NHẮN
# ==========================

def submit_chat():
    text = st.session_state.user_input.strip()
    if not text:
        return

    st.session_state.chat_history.append({"role": "user", "content": text})

    with st.spinner("⏳ Gia sư đang suy nghĩ..."):
        reply = get_gemini_response(text)

    st.session_state.chat_history.append({"role": "assistant", "content": reply})

    st.session_state.user_input = ""


# ==========================
#   GIAO DIỆN
# ==========================

st.set_page_config(page_title="Gia sư ảo", layout="centered")

st.title("👨‍🏫 Gia Sư Ảo Thông Minh")
st.markdown("---")


# FORM ĐĂNG NHẬP
def show_login():
    st.subheader("Đăng nhập để bắt đầu học")

    with st.form("login_form"):
        name = st.text_input("Họ và tên:")
        class_name = st.text_input("Lớp học:")
        submit = st.form_submit_button("Bắt đầu")

        if submit:
            handle_login(name, class_name)


# GIAO DIỆN CHAT
def show_chat():
    user = st.session_state.user_info
    st.subheader(f"Xin chào, {user['name']} (Lớp {user['class']})")
    st.markdown("---")

    if st.button("Đăng xuất"):
        st.session_state.logged_in = False
        st.session_state.chat_history = []
        st.rerun()

    # Lịch sử chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Ô nhập + nút gửi
    st.text_input("Nhập tin nhắn...", key="user_input", on_change=submit_chat)


# ==========================
#   CHẠY ỨNG DỤNG
# ==========================

if not st.session_state.logged_in:
    show_login()
else:
    show_chat()
