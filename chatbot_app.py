import streamlit as st
import requests
import base64

# --------------------------
# SETTINGS
# --------------------------
st.set_page_config(
    page_title="Gia Sư Ảo",
    layout="centered"
)

API_KEY = st.secrets["API_KEY"]
MODEL = "gemini-2.0-flash"

TEXT_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

# --------------------------
# HISTORY
# --------------------------
if "history" not in st.session_state:
    st.session_state.history = []

# --------------------------
# CALL GEMINI TEXT + IMAGE
# --------------------------
def call_gemini(prompt):
    body = { "contents": [{ "role": "user", "parts": [{ "text": prompt }]}] }

    res = requests.post(TEXT_URL, json=body)

    if res.status_code != 200:
        return None, None, f"❌ API lỗi {res.status_code}: {res.text[:200]}"

    data = res.json()

    txt = None
    img = None

    try:
        parts = data["candidates"][0]["content"]["parts"]
        for p in parts:
            if "text" in p:
                txt = p["text"]
            if "media" in p:
                img = base64.b64decode(p["media"]["data"])
    except Exception as e:
        return None, None, f"❌ Lỗi đọc dữ liệu: {e}"

    return txt, img, None


# --------------------------
# UI TITLE
# --------------------------
st.markdown("<h1 style='text-align:center;'>🤖 GIA SƯ ẢO CỦA BẠN</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; margin-top:-10px;'>ĐỀ TÀI NGHIÊN CỨU KHOA HỌC</p>", unsafe_allow_html=True)
st.markdown("---")

# --------------------------
# INPUT
# --------------------------
user_msg = st.text_area("Nhập câu hỏi:", height=120)
auto_image = st.checkbox("🎨 Tự sinh ảnh minh họa", value=True)

if st.button("Gửi") and user_msg.strip() != "":
    
    # prompt chung
    full_prompt = (
        f"Trả lời rõ ràng cho học sinh THCS. "
        f"Nếu có thể, sinh ảnh minh họa phù hợp. "
        f"Đề bài: {user_msg}"
    )

    with st.spinner("⏳ Đang xử lý..."):
        text, image, err = call_gemini(full_prompt)

    if err:
        st.error(err)
    else:
        # lưu lịch sử
        st.session_state.history.append({"q": user_msg, "a": text, "img": image})

    st.rerun()

# --------------------------
# SHOW HISTORY
# --------------------------
if st.session_state.history:
    st.markdown("## 📝 Lịch sử trao đổi")

    for item in reversed(st.session_state.history):
        st.markdown(f"**📌 Bạn:** {item['q']}")
        st.markdown(f"**🤖 Trả lời:** {item['a']}")

        if item["img"] is not None:
            st.image(item["img"], use_column_width=True)
            st.download_button("📥 Tải ảnh minh họa", item["img"], file_name="minh_hoa.png")

        st.markdown("---")
