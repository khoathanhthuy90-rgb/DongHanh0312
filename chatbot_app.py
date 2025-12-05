import streamlit as st
import requests
import json

# --- ĐỌC API KEY ---
API_KEY = st.secrets.get("API_KEY", None)

if not API_KEY:
    st.error("❌ Missing API_KEY in secrets.toml. Vui lòng thêm API_KEY vào .streamlit/secrets.toml")
    st.stop()

# --- CẤU HÌNH GEMINI ---
MODEL = "gemini-2.0-flash"

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

# --- GIAO DIỆN ---
st.title("🤖 Chat với Gemini bằng Streamlit")

prompt = st.text_area("Nhập câu hỏi của bạn:", "", height=150)

if st.button("Gửi"):
    if not prompt.strip():
        st.warning("Vui lòng nhập nội dung!")
        st.stop()

    with st.spinner("Đang xử lý..."):

        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }

        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            data = response.json()

            # Debug nếu API trả về lỗi
            # st.write(data)

            if "candidates" in data:
                answer = data["candidates"][0]["content"]["parts"][0]["text"]
                st.success("✨ Trả lời:")
                st.write(answer)
            else:
                st.error("❌ API trả về lỗi:")
                st.code(json.dumps(data, indent=2))

        except Exception as e:
            st.error(f"Lỗi không xác định: {e}")
