import streamlit as st
import requests
import time
import json

# --- CONFIG ---
# API Key must exist in .streamlit/secrets.toml
API_KEY = st.secrets.get("API_KEY", None)
MODEL = "gemini-2.5-flash-preview-09-2025"

if not API_KEY:
    st.error("❌ Missing API_KEY in secrets. Please add it to .streamlit/secrets.toml")
    st.stop()

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

# --- UI ---
st.title("Chatbot Gemini bằng Streamlit")
user_input = st.text_area("Nhập nội dung:")
btn = st.button("Gửi")

# --- CALL API ---
def call_gemini(text):
    payload = {
        "contents": [
            {"parts": [{"text": text}]}
        ]
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        return f"❌ Lỗi API: {response.status_code} - {response.text}"

    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "⚠️ Không đọc được phản hồi từ API."

# --- HANDLE ---
if btn and user_input.strip():
    with st.spinner("Đang xử lý..."):
        reply = call_gemini(user_input)
        st.write("### 🤖 Trả lời:")
        st.write(reply)
