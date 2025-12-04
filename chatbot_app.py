import streamlit as st
from google import genai
from dotenv import load_dotenv
import os
import re # Cần thiết để tìm và xử lý các thẻ hình ảnh 

# --- BƯỚC 1: Tải Khóa API và Khởi tạo Client ---
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
Bạn chỉ hướng dẫn và hỗ trợ kiến thức trong phạm vi các môn theo chương trình học hiện hành của Bộ GD&ĐT Việt Nam (Chương trình Giáo dục Phổ thông 2018).
QUY TẮC MINH HỌA: 
1. Khi giải thích các khái niệm, quy trình, hoặc công thức, hãy sử dụng các Biểu đồ, Bảng biểu Markdown, công thức toán học (LaTeX), hoặc liệt kê có cấu trúc để minh họa.
2. NẾU cần hình ảnh trực quan (như sơ đồ thí nghiệm, mô hình phân tử, hình học phức tạp, hình ảnh thực tế) để truyền đạt kiến thức, HÃY chèn tag .
   Ví dụ:  hoặc .
QUY TẮC VÀNG: Tuyệt đối KHÔNG cung cấp đáp án cuối cùng cho bài tập ngay lập tức. Thay vào đó, bạn phải hướng dẫn học sinh từng bước, đưa ra gợi ý, công thức, hoặc hỏi ngược lại để xác định lỗ hổng kiến thức.
Luôn dùng giọng điệu khuyến khích, tích cực, phù hợp với học sinh 13-14 tuổi.
"""

# --- BƯỚC 3: Quản lý Phiên (Session Management) ---

MODEL_NAME = "gemini-2.5-flash"

# LỜI CHÀO BAN ĐẦU ĐÃ CẬP NHẬT
INITIAL_GREETING = "Chào bạn! Rất vui được gặp bạn ở đây. Mình là gia sư ảo của bạn, sẵn sàng hỗ trợ bạn học tập."

if "messages" not in st.session_state:
    # Sử dụng lời chào mới
    st.session_state["messages"] = [
        {"role": "model", "text": INITIAL_GREETING}
    ]

# --- Hàm xử lý Phản hồi AI để tìm kiếm và hiển thị hình ảnh (giả) ---
def process_and_display_response(container, response_text):
    # Regex để tìm kiếm tất cả các tag 
    image_tags = re.findall(r'\[Image of\s*([^\]]+)\]', response_text)
    
    # Loại bỏ các tag  khỏi văn bản để hiển thị phần nội dung chính
    cleaned_text = re.sub(r'\[Image of\s*[^\]]+\]', '', response_text).strip()

    # 1. Hiển thị phần nội dung văn bản chính
    container.write(cleaned_text)

    # 2. Xử lý và hiển thị hình ảnh (giả)
    # Vì ứng dụng Streamlit không thể tự gọi API tạo hình ảnh (như Imagen), 
    # chúng ta sẽ hiển thị một placeholder (hộp thông báo) thay thế.
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

st.title("⭐️ Gia Sư Trực Tuyến Của Bạn") 
st.caption("Đề tài Nghiên cứu Khoa học Kỹ thuật")

# Hiển thị lịch sử trò chuyện (ĐÃ CẬP NHẬT SỬ DỤNG HÀM XỬ LÝ HÌNH ẢNH)
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["text"])
    elif msg["role"] == "model":
        with st.chat_message("assistant"):
            process_and_display_response(st.container(), msg["text"])


# Xử lý input của người dùng
if prompt := st.chat_input("Bạn có câu hỏi nào về kiến thức ở trường không?"):
    # 1. Thêm câu hỏi người dùng vào lịch sử hiển thị
    st.session_state.messages.append({"role": "user", "text": prompt})
    st.chat_message("user").write(prompt)

    # 2. Chuẩn bị lịch sử chat cho Gemini API
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
        
        # 4. Lấy phản hồi từ Gemini
        assistant_response = response.text
        
        # 5. Lưu phản hồi của AI
        st.session_state.messages.append({"role": "model", "text": assistant_response})
        
        # Hiển thị phản hồi mới nhất (ĐÃ CẬP NHẬT SỬ DỤNG HÀM XỬ LÝ HÌNH ẢNH)
        with st.chat_message("assistant"):
             process_and_display_response(st.container(), assistant_response)
            
    except Exception as e:
        # Khối except bắt lỗi và hiển thị
        st.error(f"Lỗi kết nối AI: {e}. Vui lòng kiểm tra Khóa API và trạng thái tài khoản Gemini.")

# --- Nút Xóa Lịch sử ---
if st.button("Bắt đầu Phiên Mới (Xóa lịch sử)"):
    st.session_state["messages"] = []
    st.rerun()
