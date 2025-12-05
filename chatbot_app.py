import streamlit as st
import requests
import base64
import io
from gtts import gTTS

# ======================================================
# ⚙️ CẤU HÌNH
# ======================================================
GEMINI_MODEL = "gemini-2.0-flash"
IMAGE_MODEL = "gemini-2.0-flash"     # Model hỗ trợ sinh ảnh
API_KEY = st.secrets["GEMINI_API_KEY"]

TEXT_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"
IMAGE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_MODEL}:generateImage?key={API_KEY}"

SYSTEM_INSTRUCTION = (
    "Bạn là Gia sư ảo thân thiện. Giải bài thật dễ hiểu cho học sinh cấp 2–3. "
    "Nếu học sinh chọn chế độ 'giải chi tiết', hãy giải từng bước."
)

# ======================================================
# 📌 HÀM GỌI GEMINI SINH VĂN BẢN
# ======================================================
def ask_gemini(prompt):
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    res = requests.post(TEXT_URL, json=payload)
    text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
    return text

# ======================================================
# 🖼️ HÀM GỌI GEMINI SINH ẢNH MINH HỌA
# ======================================================
def generate_image(instruction):
    payload = {
        "prompt": {
            "text": instruction
        }
    }

    res = requests.post(IMAGE_URL, json=payload)
    img_data = res.json()["image"]["imageBytes"]

    return base64.b64decode(img_data)

# ======================================================
# 🔊 TẠO GIỌNG NÓI
# ======================================================
def text_to_speech(text):
    tts = gTTS(text, lang="vi")
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# ======================================================
# 💾 LỊCH SỬ
# ======================================================
if "history" not in st.session_state:
    st.session_state.history = []

# ======================================================
# 🎨 GIAO DIỆN
# ======================================================
st.set_page_config(page_title="Gia Sư Ảo NCKH", layout="centered")

st.title("👨‍🏫 Gia Sư Ảo – Chatbot AI hỗ trợ tự học")
st.markdown("### ✨ Đề tài NCKH: *Chatbot AI – Gia sư ảo hỗ trợ học sinh tự học*")

# Chọn chế độ
mode = st.radio(
    "Chọn chế độ giải bài:",
    ["Giải nhanh", "Giải chi tiết", "Gợi mở (không cho đáp án)"]
)

question = st.text_area("Nhập bài toán:")

if st.button("Giải bài 🚀"):
    if not question.strip():
        st.error("Vui lòng nhập bài!")
        st.stop()

    # Tạo prompt theo chế độ
    if mode == "Giải nhanh":
        prompt = f"{SYSTEM_INSTRUCTION}\n\nHãy giải nhanh bài toán sau:\n{question}"
    elif mode == "Giải chi tiết":
        prompt = f"{SYSTEM_INSTRUCTION}\n\nHãy giải bài toán thật chi tiết từng bước:\n{question}"
    else:
        prompt = f"{SYSTEM_INSTRUCTION}\nKhông đưa đáp án cuối. Hãy gợi mở từng bước để học sinh tự làm:\n{question}"

    # -----------------------------
    # 🧠 AI trả lời
    # -----------------------------
    answer = ask_gemini(prompt)

    # -----------------------------
    # 🖼️ AI tạo ảnh minh họa
    # -----------------------------
    img_prompt = f"Tạo một ảnh infographic minh họa đẹp, sắc nét, phong cách giáo dục, mô tả bài toán sau: {question}"
    img_bytes = generate_image(img_prompt)

    # -----------------------------
    # 🔊 Tạo giọng nói
    # -----------------------------
    audio_file = text_to_speech(answer)

    # -----------------------------
    # 💾 Lưu vào lịch sử
    # -----------------------------
    st.session_state.history.append({
        "question": question,
        "answer": answer,
        "image": img_bytes
    })

    # -----------------------------
    # 📌 HIỂN THỊ KẾT QUẢ
    # -----------------------------
    st.subheader("📘 Lời giải:")
    st.markdown(answer)

    st.subheader("🖼️ Ảnh minh họa:")
    st.image(img_bytes, use_column_width=True)

    st.subheader("🔊 Giọng đọc lời giải:")
    st.audio(audio_file, format="audio/mp3")

    # Tải ảnh
    st.download_button(
        label="📥 Tải ảnh minh họa",
        data=img_bytes,
        file_name="minh_hoa.png",
        mime="image/png"
    )

# ======================================================
# 📚 LỊCH SỬ
# ======================================================
st.markdown("---")
st.header("📂 Lịch sử đã giải")

for i, entry in enumerate(st.session_state.history[::-1]):
    st.markdown(f"### 📝 Bài {len(st.session_state.history)-i}")
    st.write("**Đề bài:**", entry["question"])
    st.write("**Lời giải:**")
    st.markdown(entry["answer"])
    st.image(entry["image"], caption="Ảnh minh họa")
    st.markdown("---")
