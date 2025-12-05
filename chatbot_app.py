import streamlit as st
import requests

# ==============================
# ĐỌC API KEY
# ==============================
if "API_KEY" not in st.secrets:
    st.error("❌ Missing API_KEY trong secrets.toml.\n\nHãy tạo file .streamlit/secrets.toml với nội dung:\nAPI_KEY = \"YOUR_KEY_HERE\"")
    st.stop()

API_KEY = st.secrets["API_KEY"]
MODEL = "gemini-2.0-flash"

# ==============================
# HÀM GỌI GEMINI SINH VĂN BẢN
# ==============================
def generate_text(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }

    res = requests.post(url, json=body)

    if res.status_code != 200:
        return f"❌ Lỗi API {res.status_code}: {res.text}"

    try:
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return "❌ Lỗi đọc phản hồi từ API"


# ==============================
# UI - TIÊU ĐỀ
# ==============================
st.set_page_config(page_title="Gia Sư Ảo", page_icon="🤖", layout="centered")

st.markdown("""
# 🤖 GIA SƯ ẢO CỦA BẠN
### ĐỀ TÀI NGHIÊN CỨU KHOA HỌC
""")

# ==============================
# LỊCH SỬ CHAT
# ==============================
if "history" not in st.session_state:
    st.session_state.history = []

# HIỂN THỊ LỊCH SỬ
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["text"])

# ==============================
# Ô NHẬP CHAT
# ==============================
user_input = st.chat_input("Nhập câu hỏi hoặc bài học...")

if user_input:
    # Lưu tin người dùng
    st.session_state.history.append({"role": "user", "text": user_input})

    # Gửi lên giao diện
    with st.chat_message("user"):
        st.write(user_input)

    # AI trả lời
    reply = generate_text(user_input)
    st.session_state.history.append({"role": "assistant", "text": reply})

    with st.chat_message("assistant"):
        st.write(reply)

    st.rerun()
