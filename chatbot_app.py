import streamlit as st
from google import genai
from google.genai import types

# --- KHỞI TẠO VÀ KIỂM TRA API KEY ---

# Đọc khóa API từ .streamlit/secrets.toml
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]  
    # Khởi tạo Gemini Client (SDK sẽ tự động quản lý kết nối và định dạng)
    client = genai.Client(api_key=API_KEY)
except KeyError:
    st.error("❌ Missing GEMINI_API_KEY in secrets.toml.")
    st.markdown("Vui lòng thêm khóa API vào tệp `.streamlit/secrets.toml` để ứng dụng hoạt động.")
    st.stop()
except Exception as e:
    st.error(f"Lỗi khởi tạo Gemini Client: {e}")
    st.stop()

# --- CẤU HÌNH ---
MODEL = "gemini-2.5-flash"

# --- GIAO DIỆN VÀ LỊCH SỬ TRÒ CHUYỆN (SESSION STATE) ---
st.title("🤖 Chat với Gemini bằng Streamlit (Sử dụng SDK)")
st.caption(f"Đang sử dụng mô hình: **{MODEL}**")

# Khởi tạo hoặc tải lịch sử tin nhắn từ session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Hiển thị lịch sử trò chuyện trên giao diện
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- XỬ LÝ NHẬP VÀ GỬI CÂU HỎI ---

# Sử dụng st.chat_input để tạo thanh nhập tin nhắn tiện lợi
if prompt := st.chat_input("Nhập câu hỏi của bạn:"):
    
    # 1. Hiển thị tin nhắn của người dùng và lưu vào lịch sử
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Chuẩn bị dữ liệu cho API (toàn bộ lịch sử trò chuyện)
    # SDK sẽ chuyển đổi list messages thành định dạng 'contents' cần thiết
    contents = [
        types.Content(
            role=m["role"],
            parts=[types.Part.from_text(m["content"])]
        )
        for m in st.session_state["messages"]
    ]

    with st.spinner("Đang xử lý..."):
        try:
            # 3. Gọi API sử dụng client chính thức
            response = client.models.generate_content(
                model=MODEL,
                contents=contents
            )

            # 4. Hiển thị và lưu câu trả lời của Gemini
            answer = response.text
            with st.chat_message("model"):
                st.markdown(answer)

            st.session_state["messages"].append({"role": "model", "content": answer})

        except Exception as e:
            st.error(f"❌ Lỗi gọi API: {e}")
            st.warning("Kiểm tra xem Khóa API có hợp lệ không hoặc đã bị giới hạn truy cập.")

# --- Nút Xóa Lịch sử ---
st.markdown("---")
if st.button("🗑️ Xóa Lịch sử Trò chuyện"):
    st.session_state["messages"] = []
    st.rerun() # Tải lại ứng dụng để xóa giao diện
