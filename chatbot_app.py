import streamlit as st
from PIL import Image
import requests
import io

# ==============================
#  KIỂM TRA API KEY
# ==============================
API_KEY = st.secrets.get("API_KEY", None)

if not API_KEY:
    st.error("❌ Missing API_KEY in secrets. Vui lòng thêm vào `.streamlit/secrets.toml`:\n\nAPI_KEY = \"YOUR_KEY_HERE\"")
    st.stop()

# ==============================
#  GIAO DIỆN
# ==============================
st.set_page_config(page_title="Gia Sư Ảo", layout="wide")

st.title("GIA SƯ ẢO CỦA BẠN")
st.caption("ĐỀ TÀI NGHIÊN CỨU KHOA HỌC")

st.write("Nhập câu hỏi của bạn và hệ thống sẽ sinh câu trả lời hoặc hình ảnh minh hoạ.")

# Lưu lịch sử chat
if "history" not in st.session_state:
    st.session_state.history = []

# ==============================
#  TEXT INPUT
# ==============================
user_input = st.text_input("Nhập câu hỏi:")

col1, col2 = st.columns([1, 3])

with col1:
    gen_text = st.button("Sinh câu trả lời")
with col2:
    gen_image = st.button("Sinh ảnh minh hoạ")


# ==============================
#  FUNCTION: GỌI API GEMINI
# ==============================
def generate_text(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    headers = {"Content-Type": "application/json"}
    params = {"key": API_KEY}

    body = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    res = requests.post(url, headers=headers, params=params, json=body)
    data = res.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "❌ Lỗi khi sinh văn bản."


def generate_image(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    headers = {"Content-Type": "application/json"}
    params = {"key": API_KEY}

    body = {
        "contents": [{
            "parts": [{"text": f"Create an image: {prompt}"}]
        }]
    }

    res = requests.post(url, headers=headers, params=params, json=body)
    data = res.json()

    try:
        base64_img = data["candidates"][0]["content"]["parts"][0]["inline_data"]["data"]
        return Image.open(io.BytesIO(base64.b64decode(base64_img)))
    except:
        return None


# ==============================
#  HANDLE ACTIONS
# ==============================
if gen_text and user_input:
    answer = generate_text(user_input)
    st.session_state.history.append(("Bạn", user_input))
    st.session_state.history.append(("Bot", answer))

if gen_image and user_input:
    img = generate_image(user_input)
    if img:
        st.image(img, caption="Ảnh minh hoạ")
        st.session_state.history.append(("Bot (image)", "Generated image"))
    else:
        st.error("❌ Không tạo được ảnh: Không tìm thấy dữ liệu hình ảnh.")


# ==============================
#  HIỂN THỊ LỊCH SỬ CHAT
# ==============================
st.subheader("📌 Lịch sử hội thoại")

for speaker, msg in st.session_state.history:
    st.write(f"**{speaker}:** {msg}")
