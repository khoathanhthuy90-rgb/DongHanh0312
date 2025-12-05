import streamlit as st
import requests
import base64

# ==========================
# ⚙️ CẤU HÌNH API
# ==========================
GEMINI_TEXT_MODEL = "gemini-2.0-flash"
GEMINI_IMAGE_MODEL = "gemini-2.0-flash"  # flash hỗ trợ generateImage

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = None

if not API_KEY:
    st.error("⚠️ Thiếu GEMINI_API_KEY trong file secrets.toml")
    st.stop()

TEXT_API_URL = (
    f"https://generativelanguage.googleapis.com/v1/models/"
    f"{GEMINI_TEXT_MODEL}:generateContent?key={API_KEY}"
)

IMAGE_API_URL = (
    f"https://generativelanguage.googleapis.com/v1/models/"
    f"{GEMINI_IMAGE_MODEL}:generateImage?key={API_KEY}"
)

SYSTEM_INSTRUCTION = (
    "Bạn là Gia sư ảo thân thiện, giải bài cho học sinh cấp 2–3, "
    "giải thích dễ hiểu, dùng LaTeX khi cần."
)

# ==========================
# 🧩 IMAGE ENCODER
# ==========================
def get_base64_image(file):
    if file is None:
        return None
    return base64.b64encode(file.getvalue()).decode("utf-8")

# ==========================
# 🖼️ API TẠO ẢNH
# ==========================
def generate_image(prompt):
    payload = { "prompt": { "text": prompt } }

    res = requests.post(IMAGE_API_URL, json=payload)

    if res.status_code != 200:
        return None, f"❌ Lỗi ảnh: {res.text}"

    data = res.json()

    try:
        img_b64 = data["generatedImages"][0]["image"]["imageBytes"]
        return img_b64, None
    except:
        return None, f"❌ API không trả về ảnh: {data}"

# ==========================
# 🤖 API TEXT
# ==========================
def get_gemini_text(prompt, image_b64=None, has_image=False):

    content_parts = [{"text": prompt}]
    if has_image:
        content_parts.insert(0, {
            "inlineData": {
                "mimeType": "image/jpeg",
                "data": image_b64
            }
        })

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            },
            {
                "role": "user",
                "parts": content_parts
            }
        ]
    }

    res = requests.post(TEXT_API_URL, json=payload)

    if res.status_code != 200:
        return f"❌ Lỗi văn bản: {res.text}"

    try:
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "❌ Lỗi phân tích phản hồi từ API."

# ==========================
# 💾 SESSION
# ==========================
st.session_state.setdefault("messages", [])

# ==========================
# 💬 CHAT UI
# ==========================
st.set_page_config(page_title="Gia sư ảo NCKH")

st.title("👨‍🏫 Gia Sư Ảo – Tích hợp AI & Sinh ảnh minh họa")

uploaded_img = st.file_uploader("📷 Gửi ảnh bài toán (nếu có)", type=["png","jpg","jpeg"])

user_input = st.text_input("Nhập câu hỏi của bạn...")

col1, col2 = st.columns([1,1])
with col1:
    btn_send = st.button("Gửi")
with col2:
    btn_image = st.button("🖼️ Sinh ảnh minh họa")

# ==========================
# ⚙️ GỬI TIN NHẮN
# ==========================
if btn_send and (user_input or uploaded_img):

    img_b64 = get_base64_image(uploaded_img)
    has_image = uploaded_img is not None

    # Lưu message user
    st.session_state.messages.append(("user", user_input))

    # Gọi AI trả lời text
    answer = get_gemini_text(user_input, img_b64, has_image)

    st.session_state.messages.append(("bot", answer))

# ==========================
# ⚙️ SINH ẢNH MINH HOẠ
# ==========================
if btn_image and user_input:
    img_b64, err = generate_image(
        f"Minh hoạ trực quan cho bài toán: {user_input}. Phong cách đơn giản, rõ ràng."
    )

    if img_b64:
        st.session_state.messages.append(("bot_img", img_b64))
    else:
        st.session_state.messages.append(("bot", err))

# ==========================
# 📜 HIỂN THỊ LỊCH SỬ CHAT
# ==========================
st.markdown("---")

for role, msg in st.session_state.messages:
    if role == "user":
        st.markdown(f"🧑‍🎓 **Bạn:** {msg}")

    elif role == "bot":
        st.markdown(f"🤖 **Gia sư ảo:** {msg}")

    elif role == "bot_img":
        st.markdown("🖼️ **Ảnh minh họa:**")
        st.image(base64.b64decode(msg), use_column_width=True)

