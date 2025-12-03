import streamlit as st
import openai
from dotenv import load_dotenv
import os

# --- BƯỚC 1: Tải Khóa API (Đảm bảo file .env đã được tạo) ---
# Nếu bạn dùng Google Gemini, bạn cần thay bằng thư viện và khóa API của Gemini
load_dotenv()
try:
    openai.api_key = os.getenv("OPENAI_API_KEY")
except Exception:
    st.error("Lỗi: Không tìm thấy OPENAI_API_KEY. Vui lòng kiểm tra file .env!")
    st.stop()
    
# --- BƯỚC 2: Thiết lập Vai trò Sư phạm (Prompt Engineering Cốt lõi) ---
# Dùng để định hướng Chatbot trả lời theo nguyên tắc gia sư Lớp 8
SYSTEM_PROMPT = """
Bạn là Gia sư ảo chuyên nghiệp, tận tâm, thân thiện và kiên nhẫn. 
Bạn chỉ hướng dẫn và hỗ trợ kiến thức trong phạm vi Toán, Vật lý, Hóa học Lớp 8 theo chương trình học hiện hành của Bộ GD&ĐT Việt Nam.
QUY TẮC VÀNG: Tuyệt đối KHÔNG cung cấp đáp án cuối cùng cho bài tập ngay lập tức. Thay vào đó, bạn phải hướng dẫn học sinh từng bước, đưa ra gợi ý, công thức, hoặc hỏi ngược lại để xác định lỗ hổng kiến thức.
Luôn dùng giọng điệu khuyến khích, tích cực, phù hợp với học sinh 13-14 tuổi.
"""

# --- BƯỚC 3: Quản lý Phiên (Session Management) ---
# Dùng để Chatbot nhớ được lịch sử trò chuyện của từng người dùng

if "messages" not in st.session_state:
    # Khởi tạo lịch sử chat với System Prompt (để thiết lập vai trò)
    st.session_state["messages"] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

# --- BƯỚC 4: Hiển thị Giao diện Streamlit ---

st.title("🤖 Chatbot AI Gia Sư Ảo Lớp 8")
st.caption("Đề tài Nghiên cứu Khoa học Kỹ thuật")

# Hiển thị lịch sử trò chuyện
for msg in st.session_state.messages:
    if msg["role"] != "system": # Không hiển thị System Prompt
        st.chat_message(msg["role"]).write(msg["content"])

# Xử lý input của người dùng
if prompt := st.chat_input("Hãy hỏi bài tập hoặc khái niệm Lớp 8 mà bạn đang thắc mắc..."):
    # Thêm câu hỏi người dùng vào lịch sử
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Gọi API để nhận phản hồi từ Chatbot
    try:
        with st.spinner("Gia sư đang suy nghĩ..."):
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo", # Có thể nâng cấp lên gpt-4
                messages=st.session_state.messages
            )
        
        # Lấy phản hồi và hiển thị
        msg = response.choices[0].message
        st.session_state.messages.append(msg)
        st.chat_message("assistant").write(msg.content)
        
    except Exception as e:
        st.error(f"Lỗi kết nối AI: {e}. Vui lòng kiểm tra Khóa API và kết nối mạng.")

# --- Nút Xóa Lịch sử (Để kiểm tra và bắt đầu phiên mới) ---
if st.button("Bắt đầu Phiên Mới (Xóa lịch sử)"):
    st.session_state["messages"] = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.rerun()