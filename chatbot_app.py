import streamlit as st
import requests
import uuid

# ==============================
# CONFIG
# ==============================
GEMINI_MODEL = "gemini-2.5-flash-preview-09-2025"
API_KEY = ""  # <-- Nhập API KEY vào đây
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"

# ==============================
# GEMINI API
# ==============================
def ask_gemini(prompt):
    if not API_KEY:
        return "Lỗi: Bạn chưa nhập API KEY."

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [{"text": "Bạn là Gia sư ảo thân thiện, giải thích chậm rãi, dễ hiểu."}]
        }
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=20)

        if response.status_code == 200:
            data = response.json()
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        return f"Lỗi API: {response.status_code}"
    except Exception as e:
        return f"Lỗi khi gọi API: {e}"

# ==============================
# STREAMLIT APP
# ==============================
st.set_page_config(page_title="Gia Sư Ảo", page_icon="💬", layout="centered")

st.title("💬 Gia Sư Ảo (Python + Streamlit)")
st.caption("Chế độ an toàn – Không lưu trữ dữ liệu")

# Tạo session lưu lịch sử
if "messages" not in st.session_state:
    st.session_state.messages = []

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    role = "🟢 Bạn" if msg["role"] == "user" else "🤖 Gia sư ảo"
    st.markdown(f"**{role}:** {msg['content']}")

# Ô nhập
user_input = st.text_area("Nhập câu hỏi của bạn:", "")

if st.button("Gửi"):
    if user_input.strip() != "":
        # Lưu tin nhắn user
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Gọi API AI
        ai_reply = ask_gemini(user_input)

        # Lưu phản hồi AI
        st.session_state.messages.append({"role": "ai", "content": ai_reply})

        # Clear input sau khi gửi
        st.experimental_rerun()
