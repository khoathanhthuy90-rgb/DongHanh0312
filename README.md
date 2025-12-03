[chatbot_app.py](https://github.com/user-attachments/files/23917152/chatbot_app.py)# DongHanh0312
NCKH 2025
[import streamlit as st
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
    st.rerun()Uploading chatbot_app.py…]()
[requirements.txt](https://github.com/user-attachments/files/23917157/requirements.txt)
altair==5.5.0
annotated-types==0.7.0
anyio==4.12.0
attrs==25.4.0
blinker==1.9.0
Bottleneck @ file:///C:/miniconda3/conda-bld/bottleneck_1761938191468/work
cachetools==6.2.2
certifi==2025.11.12
charset-normalizer==3.4.4
click==8.3.1
colorama==0.4.6
distro==1.9.0
gitdb==4.0.12
GitPython==3.1.45
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.11
Jinja2==3.1.6
jiter==0.12.0
jsonschema==4.25.1
jsonschema-specifications==2025.9.1
MarkupSafe==3.0.3
mkl-service==2.5.2
mkl_fft @ file:///C:/miniconda3/conda-bld/mkl_fft_1761592920106/work
mkl_random @ file:///C:/miniconda3/conda-bld/mkl_random_1761593150425/work
narwhals==2.13.0
numexpr @ file:///C:/miniconda3/conda-bld/numexpr_1762165733453/work
numpy @ file:///C:/miniconda3/conda-bld/numpy_and_numpy_base_1763980698946/work/dist/numpy-2.3.5-cp311-cp311-win_amd64.whl#sha256=e3ba89fff46662b034bf265cf2c543d64ef34c25de2a336da7724a746cb8dc4e
openai==2.8.1
packaging==25.0
pandas @ file:///C:/miniconda3/conda-bld/pandas_1762332399011/work/dist/pandas-2.3.3-cp311-cp311-win_amd64.whl#sha256=6a3251bc4b4b7b67e557583d27c46e59dd38a774af7276284aaf0d4b219ca605
pillow==12.0.0
protobuf==6.33.1
pyarrow @ file:///C:/miniconda3/conda-bld/pyarrow_1759833600682/work/python
pydantic==2.12.5
pydantic_core==2.41.5
pydeck==0.9.1
python-dateutil @ file:///C:/b/abs_3au_koqnbs/croot/python-dateutil_1716495777160/work
python-dotenv==1.2.1
pytz @ file:///C:/b/abs_f8wdzeix0n/croot/pytz_1752135878094/work
referencing==0.37.0
requests==2.32.5
rpds-py==0.30.0
six @ file:///C:/b/abs_149wuyuo1o/croot/six_1744271521515/work
smmap==5.0.2
sniffio==1.3.1
streamlit==1.51.0
tenacity==9.1.2
toml==0.10.2
tornado==6.5.2
tqdm==4.67.1
typing-inspection==0.4.2
typing_extensions==4.15.0
tzdata @ file:///croot/python-tzdata_1746123641790/work
urllib3==2.5.0
watchdog==6.0.0
