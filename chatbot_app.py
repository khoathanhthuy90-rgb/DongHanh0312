import streamlit as st
import requests
import time
import json
import base64
from io import BytesIO

# ==========================
#   CẤU HÌNH API GEMINI
# ==========================
# Sử dụng mô hình đa phương thức (multimodal) chuẩn
GEMINI_MODEL = 'gemini-2.5-flash-preview-09-2025'
# API_KEY phải được để trống để Canvas tự động cung cấp
API_KEY = "" 
# Dùng phương thức xác thực qua query parameter
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"

SYSTEM_INSTRUCTION = (
    "Bạn là Gia sư ảo thân thiện và kiên nhẫn. Nhiệm vụ của bạn là giải đáp các câu hỏi "
    "về Toán, Lý, Hóa cho học sinh cấp 2 và cấp 3. Hãy: "
    "1. Đưa ra câu trả lời chi tiết, dễ hiểu, sử dụng **LaTeX** cho tất cả công thức toán học và phương trình hóa học. "
    "2. Nếu có hình ảnh, hãy phân tích hình ảnh trước khi trả lời. "
    "3. Giữ giọng điệu chuyên nghiệp nhưng khuyến khích học sinh đặt thêm câu hỏi."
)

# ==========================
#   HÀM CHUYỂN ĐỔI HÌNH ẢNH SANG BASE64
# ==========================

def get_base64_image(image_file):
    """Chuyển đổi tệp hình ảnh đã tải lên thành chuỗi base64."""
    if image_file is None:
        return None
        
    bytes_data = image_file.getvalue()
    return base64.b64encode(bytes_data).decode("utf-8")

# ==========================
#   HÀM GỌI API GEMINI (Hỗ trợ đa phương thức)
# ==========================

def get_gemini_response(prompt: str, image_data: str = None):
    """Gọi API Gemini, hỗ trợ cả text và image."""
    
    # 1. Chuẩn bị nội dung (contents)
    contents = []
    
    # Lấy file từ session state, vì nó đã được cập nhật bởi widget file_uploader
    uploaded_file_info = st.session_state.uploaded_file

    if image_data:
        # Thêm phần hình ảnh
        contents.append({
            "inlineData": {
                # Mime type của tệp tải lên
                # Cần đảm bảo file info còn tồn tại để lấy type
                "mimeType": uploaded_file_info.type if uploaded_file_info else "image/jpeg",
                "data": image_data
            }
        })
    
    # Thêm phần văn bản
    contents.append({"text": prompt})

    # Xây dựng payload
    payload = {
        "contents": [{"parts": contents}],
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
    }

    max_retries = 3
    last_code = None

    for attempt in range(max_retries):
        try:
            res = requests.post(
                API_URL, 
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
            # Log lỗi và đợi trước khi thử lại
            st.warning(f"Thử lại lần {attempt + 1}/{max_retries} thất bại. Mã trạng thái: {last_code}")
            time.sleep(1.5 * (attempt + 1))

        except Exception as e:
            # Xử lý lỗi kết nối ngoài HTTP
            return f"❌ Lỗi kết nối API: {e}"

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

if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

# ==========================
#   ĐĂNG NHẬP
# ==========================

def handle_login(name, class_name):
    """Xử lý đăng nhập, chỉ cần tên và lớp."""
    if not name or not class_name:
        st.error("⚠️ Vui lòng nhập đầy đủ thông tin.")
        return

    st.session_state.user_info = {"name": name, "class": class_name}
    st.session_state.logged_in = True

    st.session_state.chat_history = [
        {"role": "assistant", "content": f"Chào bạn, **{name} (Lớp {class_name})**! Tôi là Gia sư ảo của bạn. Bạn có thể gửi câu hỏi về Toán, Lý, Hóa (cả văn bản và hình ảnh) cho tôi."}
    ]

    st.rerun()


# ==========================
#   GỬI TIN NHẮN VÀ HÌNH ẢNH
# ==========================

def submit_chat():
    text = st.session_state.user_input.strip()
    uploaded_file = st.session_state.uploaded_file

    if not text and not uploaded_file:
        return

    image_base64 = None
    
    # 1. Xử lý hình ảnh nếu có
    if uploaded_file:
        try:
            # Lấy base64 từ file đã upload
            image_base64 = get_base64_image(uploaded_file)
            st.session_state.chat_history.append({"role": "user", "content": f"Hình ảnh đã tải lên ({uploaded_file.name})", "image": uploaded_file})
        except Exception as e:
            st.error(f"Lỗi xử lý hình ảnh: {e}")
            return
    
    # 2. Xử lý văn bản
    if text:
        st.session_state.chat_history.append({"role": "user", "content": text})

    # 3. Gọi API
    if text or uploaded_file:
        with st.spinner("⏳ Gia sư đang phân tích và suy nghĩ..."):
            reply = get_gemini_response(text, image_base64)
    
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

    # 4. Dọn dẹp
    st.session_state.user_input = ""
    # st.session_state.uploaded_file = None # BỎ DÒNG NÀY ĐỂ TRÁNH LỖI KHI XÓA VÀ GÁN LẠI WIDGET
    st.session_state["uploaded_file"] = None


# ==========================
#   GIAO DIỆN
# ==========================

st.set_page_config(page_title="Gia sư ảo của Bạn", layout="centered")

st.title("👨‍🏫 Gia Sư Ảo của Bạn")
# THÊM CỤM TỪ THEO YÊU CẦU NGAY DƯỚI TITLE
st.subheader("ĐỀ TÀI NGHIÊN CỨU KHOA HỌC") 
st.markdown("---")


# FORM ĐĂNG NHẬP
def show_login():
    st.subheader("Đăng nhập để bắt đầu học")

    with st.form("login_form"):
        # Yêu cầu tên và lớp học
        name = st.text_input("Họ và tên:", placeholder="Nguyễn Văn A")
        class_name = st.text_input("Lớp học:", placeholder="10A1")
        submit = st.form_submit_button("Bắt đầu")

        if submit:
            handle_login(name, class_name)


# GIAO DIỆN CHAT
def show_chat():
    user = st.session_state.user_info
    st.subheader(f"Xin chào, {user['name']} (Lớp {user['class']})")
    st.markdown("---")

    col_btn1, col_btn2 = st.columns([1, 6])
    with col_btn1:
        if st.button("Đăng xuất", type="primary"):
            st.session_state.logged_in = False
            st.session_state.chat_history = []
            st.rerun()

    # Khu vực lịch sử chat
    chat_container = st.container(height=400, border=True)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                if "image" in msg:
                    # Hiển thị hình ảnh đã tải lên
                    st.image(msg["image"], caption=msg["content"], width=200)
                else:
                    # Streamlit tự động render LaTeX/MathJax từ Markdown
                    st.write(msg["content"])
    
    # Vùng nhập liệu và tải tệp
    # DI CHUYỂN FILE UPLOADER RA KHỎI container ĐỂ TRÁNH XUNG ĐỘT TRẠNG THÁI
    st.file_uploader(
        "Tải lên hình ảnh bài tập (Tùy chọn):", 
        type=["png", "jpg", "jpeg"],
        key="uploaded_file", 
        accept_multiple_files=False
    )
    
    # Sử dụng st.container() cho input để giữ layout gọn gàng
    input_container = st.container()
    with input_container:
        # Ô nhập tin nhắn
        st.text_input(
            "Nhập câu hỏi của bạn:", 
            key="user_input", 
            on_change=submit_chat,
            placeholder="Ví dụ: Tính đạo hàm của hàm số $y=x^2$ hoặc giải thích hiện tượng quang điện."
        )


# ==========================
#   CHẠY ỨNG DỤNG
# ==========================

if not st.session_state.logged_in:
    show_login()
else:
    show_chat()
