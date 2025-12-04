import streamlit as st
from google import genai
from dotenv import load_dotenv
import os
import re
import uuid
import datetime
# Cần thêm thư viện json để phân tích chuỗi JSON từ Secrets
import json 

# Thư viện Firebase Admin SDK (Cần cài đặt: pip install firebase-admin)
import firebase_admin
from firebase_admin import credentials, firestore

# --- BƯỚC 1: Tải Khóa API và Khởi tạo Client Gemini ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("Lỗi: Không tìm thấy Khóa API GEMINI_API_KEY. Vui lòng dán khóa vào mục Secrets trên Streamlit Cloud.")
    st.stop()

try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"Lỗi khởi tạo Gemini Client: {e}")
    st.stop()

# --- BƯỚC 1b: Khởi tạo Firebase (ĐÃ SỬA LỖI JSON) ---
# NOTE: Cần Service Account Key từ Firebase được lưu trong st.secrets
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            # Tải khóa dịch vụ từ Streamlit Secrets
            if 'firebase_service_account' in st.secrets:
                # Lấy chuỗi JSON thô từ Secrets
                json_string = st.secrets["firebase_service_account"]
                
                # PHÂN TÍCH CHUỖI JSON thành Python Dictionary
                # Đây là bước sửa lỗi chính
                parsed_json = json.loads(json_string)
                
                # Khởi tạo Firebase bằng Dictionary đã được phân tích
                cred = credentials.Certificate(parsed_json)
                firebase_admin.initialize_app(cred)
                st.session_state['db'] = firestore.client()
            else:
                # Nếu không tìm thấy Secrets, tính năng DB sẽ bị vô hiệu hóa
                st.warning("Cảnh báo: Không tìm thấy khóa dịch vụ Firebase trong Secrets. Tính năng theo dõi sẽ bị tắt.")
                st.session_state['db'] = None
        except Exception as e:
            st.error(f"Lỗi khởi tạo Firebase: {e}")
            st.session_state['db'] = None
    elif 'db' not in st.session_state:
         st.session_state['db'] = firestore.client()

initialize_firebase()
db = st.session_state['db']

# Lấy ID ứng dụng (Dùng cho cấu trúc lưu trữ Firebase)
APP_ID = os.environ.get('CANVAS_APP_ID', 'gia-su-ao-lop-8-default')

# --- Hàm lấy ID phiên (Nhận dạng học sinh ẩn danh/Theo dõi) ---
def get_session_user_id():
    """Gán một ID UUID duy nhất cho phiên hiện tại của trình duyệt."""
    if 'session_user_id' not in st.session_state:
        # Sử dụng uuid4 để tạo ID duy nhất cho phiên
        st.session_state['session_user_id'] = str(uuid.uuid4())
    return st.session_state['session_user_id']

USER_ID = get_session_user_id()

# --- Hàm ghi nhật ký sử dụng vào Firestore ---
def log_usage(user_id, app_id, prompt_text):
    """Ghi lại một sự kiện tương tác của người dùng vào Firestore."""
    if db is None:
        return
    
    # Lưu vào collection public để dễ dàng truy vấn theo quy tắc Canvas
    collection_path = f"artifacts/{app_id}/public/data/usage_logs"
    
    try:
        db.collection(collection_path).add({
            "user_id": user_id,
            "timestamp": datetime.datetime.now(),
            "prompt": prompt_text[:200], # Chỉ lưu 200 ký tự đầu của câu hỏi
            "app_id": app_id,
            "session_id": st.session_state['session_user_id']
        })
    except Exception as e:
        print(f"Lỗi khi ghi nhật ký Firestore: {e}")

# --- Hàm lấy tổng số lần sử dụng ---
def get_usage_count(app_id):
    """Đếm tổng số tương tác đã được ghi lại."""
    if db is None:
        return "N/A (Chưa kết nối DB)"
    try:
        collection_path = f"artifacts/{app_id}/public/data/usage_logs"
        docs = db.collection(collection_path).stream()
        count = sum(1 for doc in docs)
        return count
    except Exception as e:
        print(f"Lỗi khi lấy số liệu sử dụng: {e}")
        return "Lỗi truy cập DB"


# --- BƯỚC 2: Thiết lập Vai trò Sư phạm (System Prompt) ---
SYSTEM_PROMPT = """
Bạn là Gia sư ảo chuyên nghiệp, tận tâm, thân thiện và kiên nhẫn. 
Bạn chỉ hướng dẫn và hỗ trợ kiến thức trong phạm vi Toán, Vật lý, Hóa học Lớp 8 theo chương trình học hiện hành của Bộ GD&ĐT Việt Nam (Chương trình Giáo dục Phổ thông 2018).
QUY TẮC MINH HỌA: 
1. Khi giải thích các khái niệm, quy trình, hoặc công thức, hãy sử dụng các Biểu đồ, Bảng biểu Markdown, công thức toán học (LaTeX), hoặc liệt kê có cấu trúc để minh họa.
2. NẾU cần hình ảnh trực quan (như sơ đồ thí nghiệm, mô hình phân tử, hình học phức tạp) để truyền đạt kiến thức, HÃY chèn tag .
   Ví dụ:  hoặc .
QUY TẮC VÀNG: Tuyệt đối KHÔNG cung cấp đáp án cuối cùng cho bài tập ngay lập tức. Thay vào đó, bạn phải hướng dẫn học sinh từng bước, đưa ra gợi ý, công thức, hoặc hỏi ngược lại để xác định lỗ hổng kiến thức.
Luôn dùng giọng điệu khuyến khích, tích cực, phù hợp với học sinh 13-14 tuổi.
"""

# --- BƯỚC 3: Quản lý Phiên (Session Management) ---

MODEL_NAME = "gemini-2.5-flash"
INITIAL_GREETING = "Chào bạn! Rất vui được gặp bạn ở đây. Mình là gia sư ảo của bạn, sẵn sàng hỗ trợ bạn học tập."

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "model", "text": INITIAL_GREETING}
    ]

# --- Hàm xử lý Phản hồi AI để tìm kiếm và hiển thị hình ảnh (giả) ---
def process_and_display_response(container, response_text):
    # Tìm kiếm các thẻ hình ảnh
    image_tags = re.findall(r'\[Image of\s*([^\]]+)\]', response_text)
    # Loại bỏ các thẻ hình ảnh khỏi nội dung văn bản chính
    cleaned_text = re.sub(r'\[Image of\s*[^\]]+\]', '', response_text).strip()

    container.write(cleaned_text)

    if image_tags:
        container.markdown("---")
        container.subheader("Hình Minh Họa (Phần bổ sung)")
        
        for i, description in enumerate(image_tags):
            placeholder_message = (
                f"**Hình {i+1}:** {description}\n\n"
                f"*(Gia sư ảo đã gợi ý hình ảnh minh họa cho khái niệm '{description}'. Bạn có thể tìm kiếm hình ảnh này trên Google để tham khảo.)*"
            )
            container.info(placeholder_message)
        container.markdown("---")

# --- BƯỚC 4: Hiển thị Giao diện Streamlit ---

st.title("⭐️ Gia Sư Trực Tuyến Của Tôi") 
st.caption("Đề tài Nghiên cứu Khoa học Kỹ thuật")

# Hiển thị thông tin theo dõi trong sidebar
total_logs = get_usage_count(APP_ID)
st.sidebar.header("Thông tin Theo dõi")
st.sidebar.markdown(f"**Mã Session (Học sinh):** `{USER_ID}`")
st.sidebar.markdown(f"**Tổng số lần tương tác:** `{total_logs}`")
st.sidebar.markdown("---")
st.sidebar.markdown("Kiểm tra **Firebase Console** để xem chi tiết nhật ký sử dụng tại collection `usage_logs`.")


# Hiển thị lịch sử trò chuyện (ĐÃ CẬP NHẬT SỬ DỤNG HÀM XỬ LÝ HÌNH ẢNH)
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["text"])
    elif msg["role"] == "model":
        with st.chat_message("assistant"):
            process_and_display_response(st.container(), msg["text"])


# Xử lý input của người dùng
if prompt := st.chat_input("Bạn có câu hỏi nào về Toán, Lý, Hóa lớp 8 không?"):
    st.session_state.messages.append({"role": "user", "text": prompt})
    st.chat_message("user").write(prompt)

    gemini_history = [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in st.session_state.messages]
    
    try:
        with st.spinner("Gia sư đang suy nghĩ..."):
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=gemini_history,
                config={"system_instruction": SYSTEM_PROMPT}
            )
        
        assistant_response = response.text
        
        # 5. Lưu phản hồi của AI và ghi nhật ký sử dụng
        st.session_state.messages.append({"role": "model", "text": assistant_response})
        log_usage(USER_ID, APP_ID, prompt) # GHI NHẬT KÝ VÀO FIRESTORE
        
        # Hiển thị phản hồi mới nhất
        with st.chat_message("assistant"):
             process_and_display_response(st.container(), assistant_response)
             
        # Tự động reload để cập nhật số liệu trong sidebar
        st.experimental_rerun()
            
    except Exception as e:
        st.error(f"Lỗi kết nối AI: {e}. Vui lòng kiểm tra Khóa API và trạng thái tài khoản Gemini.")

# --- Nút Xóa Lịch sử ---
if st.button("Bắt đầu Phiên Mới (Xóa lịch sử)"):
    st.session_state["messages"] = []
    st.rerun()
