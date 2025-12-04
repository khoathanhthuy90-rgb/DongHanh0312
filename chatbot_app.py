import streamlit as st
import requests
import time
import json

# --- CẤU HÌNH API GEMINI ---
# Cấu hình API Gemini
GEMINI_MODEL = 'gemini-2.5-flash-preview-09-2025'
# API_KEY sẽ được Canvas cung cấp tự động trong môi trường runtime
API_KEY = "" 
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"
# --- KẾT THÚC CẤU HÌNH API ---

# --- KHỞI TẠO TRẠNG THÁI (Mô phỏng DB và Session) ---

# Nếu không có, khởi tạo trạng thái phiên (session state)
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = {}
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
# Mô phỏng database để lưu trữ dữ liệu người dùng và tần suất đăng nhập
# Key: Tên + Lớp (vd: "Nguyễn Văn A - 10A1") | Value: {'name': str, 'class': str, 'login_count': int}
if 'user_data_db' not in st.session_state:
    st.session_state['user_data_db'] = {}

# --- LOGIC GỌI API GEMINI (Đồng bộ) ---

def get_gemini_response(prompt):
    """Gọi API Gemini để lấy phản hồi từ Gia sư ảo."""
    # System Instruction định nghĩa vai trò của AI
    system_instruction = "Bạn là Gia sư ảo thân thiện và kiên nhẫn. Nhiệm vụ của bạn là giải đáp các câu hỏi về Toán, Lý, Hóa cho học sinh cấp 2 và cấp 3. Hãy đưa ra câu trả lời chi tiết, dễ hiểu và khuyến khích học sinh đặt thêm câu hỏi."
    
    # Xây dựng payload cho API
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]}
    }

    try:
        max_retries = 3
        for retry_count in range(max_retries):
            # Thực hiện POST request
            response = requests.post(
                API_URL, 
                headers={'Content-Type': 'application/json'},
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                result = response.json()
                # Trích xuất nội dung từ phản hồi
                text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "Xin lỗi, tôi không thể tìm thấy câu trả lời.")
                return text
            
            # Nếu thất bại, đợi với Exponential Backoff
            wait_time = (2 ** retry_count) * 1
            if retry_count < max_retries - 1:
                time.sleep(wait_time)
            
        return "Xin lỗi, tôi đang gặp lỗi kết nối API sau nhiều lần thử. Vui lòng thử lại sau."

    except Exception as e:
        st.error(f"Lỗi không xác định khi gọi API: {e}")
        return "Xin lỗi, đã xảy ra lỗi không xác định. Vui lòng kiểm tra lại kết nối."

# --- LOGIC XỬ LÝ ĐĂNG NHẬP ---

def handle_login(name, class_name):
    """Xử lý logic đăng nhập, cập nhật DB mô phỏng và trạng thái."""
    if not name or not class_name:
        st.error("Vui lòng nhập đầy đủ Họ tên và Lớp học.")
        return False

    key = f"{name} - {class_name}"
    
    # 1. Kiểm tra và cập nhật DB mô phỏng (tần suất đăng nhập)
    if key in st.session_state['user_data_db']:
        st.session_state['user_data_db'][key]['login_count'] += 1
    else:
        st.session_state['user_data_db'][key] = {
            'name': name,
            'class': class_name,
            'login_count': 1
        }
        
    # 2. Cập nhật trạng thái phiên
    st.session_state['user_info'] = st.session_state['user_data_db'][key]
    st.session_state['logged_in'] = True
    st.session_state['chat_history'] = [
        {"role": "assistant", "content": f"Chào mừng bạn, **{name} - Lớp {class_name}**! Tôi là Gia sư ảo của bạn. Bạn đã đăng nhập **{st.session_state['user_info']['login_count']}** lần. Hãy hỏi tôi bất cứ điều gì về Toán, Lý, Hóa nhé!"}
    ]
    # Bỏ st.rerun() vì form submission đã tự động kích hoạt một lần chạy lại script.
    return True

# --- LOGIC XỬ LÝ CHAT ---

def handle_chat_input():
    """Xử lý đầu vào chat từ người dùng và gọi API."""
    user_input = st.session_state.chat_input
    if user_input:
        # 1. Thêm tin nhắn người dùng vào lịch sử
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # 2. Hiển thị trạng thái chờ và gọi API
        with st.spinner("Gia sư ảo đang suy nghĩ..."):
            ai_response = get_gemini_response(user_input)
        
        # 3. Thêm phản hồi của AI vào lịch sử
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        st.session_state.chat_input = "" # Xóa input sau khi gửi
        # Bỏ st.rerun() vì việc cập nhật session state trong callback sẽ tự động kích hoạt
        # một lần chạy lại script để cập nhật giao diện chat.

# --- GIAO DIỆN STREAMLIT ---

st.set_page_config(page_title="Gia Sư Ảo Streamlit", layout="centered")

st.title("👨‍🏫 Gia Sư Ảo AI - Toán, Lý, Hóa")
st.markdown("---")


# Hàm hiển thị form Đăng nhập
def show_login_form():
    """Hiển thị form đăng nhập cho học sinh."""
    st.subheader("Nhập thông tin để bắt đầu")
    
    with st.form("login_form"):
        st.info("Chúng tôi yêu cầu Họ tên và Lớp học để theo dõi tần suất đăng nhập của bạn.")
        
        name = st.text_input("Họ và Tên:", placeholder="Ví dụ: Nguyễn Văn A")
        class_name = st.text_input("Lớp học:", placeholder="Ví dụ: 10A1")
        
        submitted = st.form_submit_button("Bắt đầu chat với Gia sư")
        
        if submitted:
            # handle_login sẽ được gọi và form submission tự động gây ra re-run
            handle_login(name, class_name)

# Hàm hiển thị giao diện Chat
def show_chat_interface():
    """Hiển thị giao diện chat và dashboard người dùng."""
    
    user_data = st.session_state.user_info
    
    # Hiển thị Dashboard người dùng
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("https://placehold.co/100x100/10B981/ffffff?text=AI+Tutor", width=80)
    with col2:
        st.subheader(f"Xin chào, {user_data['name']}!")
        st.markdown(f"**Lớp:** {user_data['class']}")
        st.markdown(f"**Tần suất đăng nhập:** `{user_data['login_count']}` lần (Được lưu trong bộ nhớ tạm)")
        st.markdown("---")
        
    # Nút Đăng xuất
    if st.button("Đăng xuất", type="primary"):
        st.session_state['logged_in'] = False
        st.session_state['user_info'] = {}
        st.session_state['chat_history'] = []
        st.rerun() # Giữ lại st.rerun() ở đây để ngay lập tức chuyển về màn hình đăng nhập

    # Khu vực hiển thị tin nhắn
    for message in st.session_state.chat_history:
        role = "assistant" if message["role"] == "assistant" else "user"
        with st.chat_message(role):
            st.markdown(message["content"])

    # Khu vực nhập tin nhắn
    st.chat_input("Hỏi Gia sư về Toán, Lý, Hóa...", key="chat_input", on_submit=handle_chat_input, disabled=False)

# --- CHẠY ỨNG DỤNG CHÍNH ---

if not st.session_state['logged_in']:
    show_login_form()
else:
    show_chat_interface()
