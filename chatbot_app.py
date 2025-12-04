import streamlit as st
import requests
import time
import json

# ==========================
#   CẤU HÌNH API GEMINI (ĐÃ ĐƯỢC SỬA ĐỂ PHÙ HỢP VỚI MÔI TRƯỜNG CANVAS)
# ==========================
# SỬ DỤNG MÔ HÌNH VÀ CÁCH XÁC THỰC CHUẨN TRONG MÔI TRƯỜNG NÀY
GEMINI_MODEL = 'gemini-2.5-flash-preview-09-2025'

# API_KEY phải được để trống (như thế này: "") để Canvas tự động cung cấp trong runtime
API_KEY = "" 

# Dùng API Key qua query parameter (?key=...)
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"

SYSTEM_INSTRUCTION = (
    "Bạn là Gia sư ảo thân thiện và kiên nhẫn. "
    "Nhiệm vụ của bạn là giải đáp các câu hỏi về Toán, Lý, Hóa cho học sinh cấp 2 và cấp 3. "
    "Hãy đưa ra câu trả lời chi tiết, dễ hiểu và khuyến khích học sinh đặt thêm câu hỏi."
)

# ==========================
#   HÀM GỌI API GEMINI
# ==========================

def get_gemini_response(prompt: str):
    # Cấu trúc payload đúng cho generateContent khi dùng system instruction
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        # systemInstruction phải là thuộc tính cấp cao nhất
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
    }

    max_retries = 3
    last_code = None

    for attempt in range(max_retries):
        try:
            # Gửi yêu cầu POST, headers chỉ cần Content-Type
            res = requests.post(
                API_URL, 
                # Không cần header "Authorization"
                headers={'Content-Type': 'application/json'}, 
                data=json.dumps(payload)
            )

            if res.status_code == 200:
                data = res.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "Xin lỗi, tôi không tìm thấy câu trả lời.")
                )
                return text

            last_code = res.status_code
            st.warning(f"Thử lại lần {attempt + 1}/{max_retries} thất bại. Mã trạng thái: {last_code}")
            time.sleep(1.5 * (attempt + 1))

        except Exception as e:
            return f"❌ Lỗi kết nối API không xác định: {e}"

    # Xử lý lỗi sau khi hết lần thử
    error_message = f"❌ Lỗi API nghiêm trọng: Không thể kết nối sau {max_retries} lần thử. Mã trạng thái cuối cùng: {last_code}"
    
    if last_code == 403 or last_code == 401:
        st.error(f"{error_message}. **Đây là lỗi Xác thực (API Key).** Vui lòng tải lại Canvas để đảm bảo API Key được cung cấp chính xác.")
    else:
        st.error(error_message)
        
    return "Xin lỗi, tôi đang gặp lỗi kết nối API sau nhiều lần thử. Vui lòng thử lại sau."


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
        # Lỗi 403/401 sẽ xuất hiện ở đây nếu API Key bị lỗi
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
    # Sử dụng on_change để submit_chat được gọi khi bấm Enter hoặc focus ra khỏi ô input
    st.text_input("Nhập tin nhắn...", key="user_input", on_change=submit_chat, placeholder="Hỏi Gia sư về Toán, Lý, Hóa...")


# ==========================
#   CHẠY ỨNG DỤNG
# ==========================

if not st.session_state.logged_in:
    show_login()
else:
    show_chat()
