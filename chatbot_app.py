# GIA SƯ ẢO CỦA BẠN
# ĐỀ TÀI NGHIÊN CỨU KHOA HỌC (nhỏ dưới tiêu đề)

import streamlit as st
import requests
import base64
import time

# =======================
# CONFIG
# =======================
API_KEY = st.secrets.get("API_KEY", None)
MODEL_NAME = "gemini-2.0-flash-lite-preview"  # model hỗ trợ sinh ảnh

if not API_KEY:
    st.error("Thiếu API_KEY trong secrets.toml")
    st.stop()

# =======================
# PAGE UI
# =======================
st.set_page_config(page_title="Gia Sư Ảo", page_icon="🤖", layout="centered")

st.markdown(
    """
    <h1 style="text-align:center;">🤖 GIA SƯ ẢO CỦA BẠN</h1>
    <p style="text-align:center; font-size:18px; color:#666; margin-top:-12px;">
        ĐỀ TÀI NGHIÊN CỨU KHOA HỌC
    </p>
    <hr>
    """,
    unsafe_allow_html=True,
)

# =======================
# Lưu lịch sử (text + image luôn đi kèm)
# =======================
if "history" not in st.session_state:
    st.session_state.history = []  # mỗi entry: {"q":..., "a":..., "img":...}

# =======================
# API TEXT
# =======================
def call_gemini_text(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    body = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}    
        ]
    }
    r = requests.post(url, json=body)
    if r.status_code != 200:
        return f"❌ Lỗi API Text {r.status_code}: {r.text[:200]}"
    try:
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "❌ Không đọc được kết quả văn bản"

# =======================
# API IMAGE
# =======================
def call_gemini_image(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    body = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}    
        ]
    }
    r = requests.post(url, json=body)
    if r.status_code != 200:
        return None, f"❌ Lỗi API Ảnh {r.status_code}: {r.text[:200]}"
    try:
        parts = r.json()["candidates"][0]["content"]["parts"]
        for p in parts:
            if "media" in p:
                return p["media"]["data"], None
        return None, "❌ Không tìm thấy ảnh trong phản hồi"
    except Exception as e:
        return None, f"❌ Lỗi đọc dữ liệu ảnh: {e}"

# =======================
# INPUT
# =======================
user_q = st.text_area("Nhập câu hỏi của bạn:")

if st.button("Gửi câu hỏi") and user_q.strip():
    with st.spinner("Đang tạo lời giải..."):
        answer = call_gemini_text(user_q)

    with st.spinner("Đang tạo ảnh minh họa..."):
        img_data, err = call_gemini_image(f"Hãy tạo hình minh họa rõ ràng cho bài toán: {user_q}")

    if err:
        st.warning(err)
        img_bytes = None
    else:
        img_bytes = base64.b64decode(img_data)

    st.session_state.history.append({
        "q": user_q,
        "a": answer,
        "img": img_bytes
    })

    st.rerun()

# =======================
# HIỂN THỊ LỊCH SỬ — SẠCH, GỌN, CHỈ TEXT + ẢNH
# =======================
st.subheader("📘 Lịch sử trao đổi")
for item in reversed(st.session_state.history):
    st.markdown(f"**🧑‍🎓 Câu hỏi:** {item['q']}")
    st.markdown(f"**🤖 Trả lời:** {item['a']}")
    if item["img"]:
        st.image(item["img"], caption="Ảnh minh họa AI tạo", use_column_width=True)
        st.download_button("Tải ảnh minh họa", item["img"], "minh_hoa.png")
    st.markdown("<hr>", unsafe_allow_html=True)
