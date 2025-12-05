# app.py
import streamlit as st
import requests
import base64
import uuid
from datetime import datetime

# --------------------------
# CẤU HÌNH
# --------------------------
GEMINI_TEXT_MODEL = "gemini-2.0-flash"
GEMINI_IMAGE_MODEL = "gemini-2.0-flash"  # model generateImage (flash)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = None

if not API_KEY:
    st.error("Thiếu GEMINI_API_KEY trong .streamlit/secrets.toml")
    st.stop()

TEXT_API_URL = (
    f"https://generativelanguage.googleapis.com/v1/models/"
    f"{GEMINI_TEXT_MODEL}:generateContent?key={API_KEY}"
)
IMAGE_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_IMAGE_MODEL}:generateImage?key={API_KEY}"
)

SYSTEM_INSTRUCTION = (
    "Bạn là gia sư ảo thân thiện, giải bài cho học sinh cấp 2–3. "
    "Trình bày rõ ràng, có thể dùng LaTeX cho công thức khi cần."
)

# --------------------------
# SESSION STATE INIT
# --------------------------
st.set_page_config(page_title="Gia Sư Ảo – Sinh Ảnh Minh Họa", layout="wide")
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # list of dicts: {"role","text","time"}
if "image_history" not in st.session_state:
    st.session_state.image_history = []  # list of dicts: {"id","question","b64","style","time"}

# --------------------------
# HỖ TRỢ: prompt style mapping
# --------------------------
STYLE_PROMPT_MAP = {
    "Sơ đồ toán học (diagram)": "diagram-style, clear labels, vector lines, simple shapes, white background, black axis lines, no extraneous decoration",
    "Minh họa đơn giản (simple illustration)": "flat simple illustration, clean colors, educational style, minimal text, clear shapes",
    "Tranh hoạt hình (cartoon)": "cartoon style, friendly characters, colorful, playful, simplified shapes",
    "Phong cách sách giáo khoa (textbook style)": "textbook illustration, clear labeled parts, muted colors, high clarity suitable for textbooks",
    "Ảnh thật (realistic)": "photo-realistic, realistic lighting, natural textures, high resolution, clear composition"
}

# --------------------------
# HÀM GỌI GEMINI (TEXT)
# --------------------------
def call_gemini_text(user_prompt: str):
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": SYSTEM_INSTRUCTION}]},
            {"role": "user", "parts": [{"text": user_prompt}]}
        ]
    }
    try:
        res = requests.post(TEXT_API_URL, json=payload, timeout=30)
    except Exception as e:
        return None, f"Lỗi kết nối API (text): {e}"

    if res.status_code != 200:
        return None, f"API text trả lỗi {res.status_code}: {res.text[:300]}"

    try:
        data = res.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text, None
    except Exception as e:
        return None, f"Lỗi phân tích JSON text: {e}"

# --------------------------
# HÀM GỌI GEMINI (IMAGE)
# --------------------------
def call_gemini_image(image_prompt: str):
    """
    Gọi API generateImage. Trả về image_base64 (chuỗi) hoặc (None, err)
    """
    payload = {"prompt": image_prompt}
    try:
        res = requests.post(IMAGE_API_URL, json=payload, timeout=60)
    except Exception as e:
        return None, f"Lỗi kết nối API (image): {e}"

    if res.status_code != 200:
        return None, f"API image trả lỗi {res.status_code}: {res.text[:300]}"

    try:
        data = res.json()
    except Exception as e:
        return None, f"Lỗi decode JSON image: {e}. Raw: {res.text[:400]}"

    # Kiểm tra field đúng chuẩn
    if "generatedImages" not in data:
        return None, f"API không trả generatedImages. Response: {data}"

    try:
        img_b64 = data["generatedImages"][0]["image"]["imageBytes"]
        return img_b64, None
    except Exception as e:
        return None, f"Lỗi lấy imageBytes: {e}. Data: {data}"

# --------------------------
# UI: thanh bên cài đặt
# --------------------------
with st.sidebar:
    st.header("Cài đặt ảnh minh họa")
    style = st.selectbox("Chọn phong cách ảnh:", list(STYLE_PROMPT_MAP.keys()))
    seed_info = st.text_input("Thông tin bổ sung cho ảnh (tùy chọn):", placeholder="ví dụ: 'nhãn: a,b; high contrast'")
    st.markdown("---")
    st.markdown("Hướng dẫn ngắn:")
    st.write("- Chọn phong cách phù hợp với dạng bài.")
    st.write("- Nhấp 'Sinh ảnh minh họa' để chỉ tạo ảnh.")
    st.write("- Nhấp 'Gửi & Sinh ảnh' để vừa lấy lời giải vừa sinh ảnh.")

# --------------------------
# UI: chính
# --------------------------
st.title("👨‍🏫 Gia Sư Ảo – Tích hợp AI & Sinh ảnh minh họa")
st.markdown("Nhập đề bài hoặc câu hỏi, chọn phong cách ảnh rồi chọn hành động.")

col_input, col_actions = st.columns([4,1])
with col_input:
    user_q = st.text_area("Nhập câu hỏi / đề bài:", height=150)
with col_actions:
    btn_send = st.button("Gửi & Sinh ảnh")
    btn_only_image = st.button("Chỉ sinh ảnh minh họa")
    st.write("")
    st.write("")

# --------------------------
# XỬ LÝ NÚT: Sinh ảnh (chỉ ảnh)
# --------------------------
def make_image_and_store(question_text, style_key, extra_info=""):
    # build image prompt
    style_desc = STYLE_PROMPT_MAP.get(style_key, "")
    prompt = f"Create an educational, {style_key}. {style_desc}. Illustrate the following math problem clearly for middle school students: {question_text}."
    if extra_info:
        prompt += " Additional instructions: " + extra_info

    img_b64, err = call_gemini_image(prompt)
    timestamp = datetime.utcnow().isoformat()
    if img_b64:
        img_id = str(uuid.uuid4())
        st.session_state.image_history.append({
            "id": img_id,
            "question": question_text,
            "b64": img_b64,
            "style": style_key,
            "time": timestamp
        })
        return img_b64, None
    else:
        return None, err

if btn_only_image and user_q.strip():
    with st.spinner("⏳ Đang sinh ảnh minh họa... Vui lòng chờ (có thể mất vài chục giây)"):
        img_b64, err = make_image_and_store(user_q, style, seed_info)
    if img_b64:
        st.success("✅ Ảnh minh họa đã tạo xong.")
        st.image(base64.b64decode(img_b64), use_column_width=True)
        # download button
        st.download_button("📥 Tải ảnh minh họa", data=base64.b64decode(img_b64),
                           file_name="minh_hoa.png", mime="image/png")
    else:
        st.error(f"❌ Lỗi khi sinh ảnh: {err}")

# --------------------------
# XỬ LÝ NÚT: Gửi & Sinh ảnh (both)
# --------------------------
if btn_send and user_q.strip():
    # 1) Lấy lời giải (text)
    with st.spinner("⏳ Đang tạo lời giải..."):
        answer_text, err_text = call_gemini_text(user_q)
    if err_text:
        st.error(err_text)
    else:
        # hiển thị lời giải
        st.subheader("📘 Lời giải")
        st.markdown(answer_text)

        # lưu chat lịch sử
        st.session_state.chat_history.append({
            "role": "user", "text": user_q, "time": datetime.utcnow().isoformat()
        })
        st.session_state.chat_history.append({
            "role": "bot", "text": answer_text, "time": datetime.utcnow().isoformat()
        })

        # 2) Sinh ảnh minh họa
        with st.spinner("🎨 Đang sinh ảnh minh họa... (có thể mất vài chục giây)"):
            img_b64, img_err = make_image_and_store(user_q, style, seed_info)

        if img_b64:
            st.success("✅ Ảnh minh họa đã tạo")
            st.image(base64.b64decode(img_b64), use_column_width=True)
            st.download_button("📥 Tải ảnh minh họa", data=base64.b64decode(img_b64),
                               file_name="minh_hoa.png", mime="image/png")
        else:
            st.error(f"❌ Lỗi tạo ảnh: {img_err}")

# --------------------------
# HIỂN THỊ NHẬT KÝ ẢNH (image_history)
# --------------------------
st.markdown("---")
st.header("📂 Nhật ký ảnh minh họa")
if not st.session_state.image_history:
    st.info("Chưa có ảnh minh họa nào. Tạo 1 ảnh bằng nút 'Chỉ sinh ảnh' hoặc 'Gửi & Sinh ảnh'.")
else:
    # hiển thị các ảnh gần nhất lên top
    for entry in reversed(st.session_state.image_history):
        col1, col2 = st.columns([1,3])
        with col1:
            try:
                st.image(base64.b64decode(entry["b64"]), width=160)
            except Exception:
                st.write("⚠️ Lỗi hiển thị ảnh")
        with col2:
            st.markdown(f"**Đề bài:** {entry['question']}")
            st.markdown(f"- **Phong cách:** {entry['style']}")
            st.markdown(f"- **Thời gian:** {entry['time']}")
            # download + view full
            st.download_button("📥 Tải ảnh", data=base64.b64decode(entry["b64"]),
                               file_name=f"minh_hoa_{entry['id']}.png", mime="image/png")
        st.markdown("---")

# --------------------------
# HIỂN THỊ LỊCH SỬ LỜI GIẢI (chat_history)
# --------------------------
st.markdown("---")
st.header("📝 Lịch sử lời giải (gần đây)")
if not st.session_state.chat_history:
    st.info("Chưa có lời giải nào. Nhập đề bài và bấm Gửi & Sinh ảnh.")
else:
    for m in st.session_state.chat_history[-6:]:
        role_emoji = "🧑‍🎓" if m["role"] == "user" else "🤖"
        st.write(f"{role_emoji} {m['text']}")
