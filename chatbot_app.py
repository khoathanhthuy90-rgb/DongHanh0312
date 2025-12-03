import streamlit as st
from google import genai
from dotenv import load_dotenv
import os

# --- BƯỚC 1: Tải Khóa API và Khởi tạo Client ---
# Ghi chú: Sử dụng GEMINI_API_KEY
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


# --- BƯỚC 2: Thiết lập Vai trò Sư phạm (System Prompt) ---
SYSTEM_PROMPT = """
Bạn là Gia sư ảo chuyên nghiệp, tận tâm, thân thiện và kiên nhẫn. 
Bạn chỉ hướng dẫn và hỗ trợ kiến thức trong phạm vi Toán, Vật lý, Hóa học Lớp 8 theo chương trình học hiện hành của Bộ GD&ĐT Việt Nam.
QUY TẮC VÀNG: Tuyệt đối KHÔNG cung cấp đáp án cuối cùng cho bài tập ngay lập tức. Thay vào đó, bạn phải hướng dẫn học sinh từng bước, đưa ra gợi ý, công thức, hoặc hỏi ngược lại để xác định lỗ hổng kiến thức.
Luôn dùng giọng điệu khuyến khích, tích cực, phù hợp với học sinh 13-14 tuổi.
"""

# --- BƯỚC 3: Quản lý Phiên (Session Management) ---

MODEL_NAME = "gemini-2.5-flash"

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- BƯỚC 4: Hiển thị Giao diện Streamlit ---

st.title("🤖 Chatbot AI Gia Sư Ảo Lớp 8")
st.caption("Đề tài Nghiên cứu Khoa học Kỹ thuật")

# Hiển thị lịch sử trò chuyện
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["text"])
    elif msg["role"] == "model":
        st.chat_message("assistant").write(msg["text"])

# Xử lý input của người dùng
if prompt := st.chat_input("Hãy hỏi bài tập hoặc khái niệm Lớp 8 mà bạn đang thắc mắc..."):
    # 1. Thêm câu hỏi người dùng vào lịch sử hiển thị
    st.session_state.messages.append({"role": "user", "text": prompt})
    st.chat_message("user").write(prompt)

    # 2. Chuẩn bị lịch sử chat cho Gemini API
    # Chuyển đổi định dạng Streamlit sang định dạng Gemini
    gemini_history = [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in st.session_state.messages]
    
    try:
        with st.spinner("Gia sư đang suy nghĩ..."):
            # 3. Gọi API để nhận phản hồi từ Chatbot
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=gemini_history,
                config={
                    "system_instruction": SYSTEM_PROMPT 
                }
            )
        
        # 4. Lấy phản hồi từ Gemini và hiển thị
        assistant_response = response.text
        
        # 5. Hiển thị và Lưu phản hồi của AI
        st.session_state.messages.append({"role": "model", "text": assistant_response})
        st.chat_message("assistant").write(assistant_response)
            
    except Exception as e:
        # Khối except bắt lỗi và hiển thị
        st.error(f"Lỗi kết nối AI: {e}. Vui lòng kiểm tra Khóa API và trạng thái tài khoản Gemini.")

# --- Nút Xóa Lịch sử ---
if st.button("Bắt đầu Phiên Mới (Xóa lịch sử)"):
    st.session_state["messages"] = []
    st.rerun()
