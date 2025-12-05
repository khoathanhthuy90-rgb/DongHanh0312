import streamlit as st
import requests
import base64

# ==============================
# ĐỌC API KEY
# ==============================
if "API_KEY" not in st.secrets:
    st.error("❌ Missing API_KEY in secrets.toml")
    st.stop()

API_KEY = st.secrets["API_KEY"]
MODEL = "gemini-2.0-flash"

# ==============================
# HÀM GỌI GEMINI SINH VĂN BẢN
# ==============================
def generate_text(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
    body = { "contents": [{"role": "user", "parts": [{"text": prompt}]}] }

    res = requests.post(url, json=body)
    if res.status_code != 200:
        return f"❌ Lỗi API {res.status_code}: {res.text}"

    try:
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "❌ Lỗi đọc response văn bản"

# ==============================
# HÀM GỌI GEMINI SINH ẢNH
# ==============================
def generate_image(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
    body = { "contents": [{"role": "user", "parts": [{"text": prompt}]}] }

    res = requests.post(url, json=body)
    if res.status_code != 200:
        return None, f"❌ Lỗi API {res.status_code}: {res.text}"

    try:
        parts = res.json()["candidates"][0]["content"]["parts"]
        for p in parts:
            if "media" in p:
                img_bytes = base64.b64decode(p["media"]["data"])
                return img_bytes, None
        return None, "❌ Không tìm thấy ảnh trong phản hồi!"
    except Exception as e:
        return None, f"❌ Lỗi đọc ảnh: {e}"

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

# HIỂN THỊ CHAT
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.write(msg["text"])
        if msg.get("image"):
            st.image(msg["image"], caption="Ảnh minh họa AI")

# ==============================
# Ô NHẬP CHAT
# ==============================
user_input = st.chat_input("Nhập câu hỏi hoặc bài học của bạn...")

if user_input:
    # Lưu tin người dùng
    st.session_state.history.append({"role": "user", "text": user_input})

    # --- Gọi AI sinh văn bản ---
    with st.chat_message("assistant"):
        st.write("⏳ Đang xử lý...")

        reply = generate_text(user_input)

        st.session_state.history.append({"role": "assistant", "text": reply})
        st.write(reply)

        # --- Tự sinh ảnh đi kèm ---
        img_prompt = f"Tạo ảnh minh họa rõ ràng, đẹp, cho nội dung: {user_input}"

        img_bytes, err = generate_image(img_prompt)

        if img_bytes and not err:
            st.image(img_bytes, caption="Ảnh minh họa AI")
            st.session_state.history[-1]["image"] = img_bytes
        else:
            st.warning(err)

    st.rerun()
