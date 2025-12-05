import streamlit as st
import requests
import base64

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Gia Sư Ảo", page_icon="🤖", layout="centered")
API_KEY = st.secrets["API_KEY"]
MODEL_NAME = "gemini-2.0-flash"

# -----------------------------
# STYLE – Messenger UI
# -----------------------------
st.markdown(
    """
    <style>
        body { background-color: #f0f2f5; }
        .title-main { text-align:center; font-size:36px; font-weight:700; margin-bottom: -10px; }
        .title-sub { text-align:center; font-size:18px; color:#666; margin-bottom:30px; }

        .chat-container {
            width: 100%;
            max-width: 650px;
            margin: auto;
        }
        .bubble-user {
            background: #0084ff;
            color: white;
            padding: 12px 16px;
            border-radius: 18px 18px 0 18px;
            margin: 10px 0;
            max-width: 75%;
            float: right;
            clear: both;
        }
        .bubble-bot {
            background: #e4e6eb;
            padding: 12px 16px;
            border-radius: 18px 18px 18px 0;
            margin: 10px 0;
            max-width: 75%;
            float: left;
            clear: both;
        }
        .avatar-user, .avatar-bot {
            width: 38px; height: 38px;
            border-radius: 50%;
            margin: 5px;
        }
        .row { display:flex; align-items: flex-end; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# SESSION STATE
# -----------------------------
if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------
# CALL GEMINI TEXT
# -----------------------------
def gen_text(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    res = requests.post(url, json=body)
    try:
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "❌ Lỗi: Không đọc được phản hồi AI"

# -----------------------------
# CALL GEMINI IMAGE
# -----------------------------
def gen_image(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    res = requests.post(url, json=body)
    data = res.json()
    try:
        parts = data["candidates"][0]["content"]["parts"]
        for p in parts:
            if "media" in p:
                return base64.b64decode(p["media"]["data"])
        return None
    except:
        return None

# -----------------------------
# TITLES
# -----------------------------
st.markdown("<div class='title-main'>GIA SƯ ẢO CỦA BẠN</div>", unsafe_allow_html=True)
st.markdown("<div class='title-sub'>ĐỀ TÀI NGHIÊN CỨU KHOA HỌC</div>", unsafe_allow_html=True)

st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

# -----------------------------
# SHOW HISTORY (Messenger style)
# -----------------------------
for msg in st.session_state.history:
    if msg["role"] == "user":
        st.markdown(
            f"<div class='row' style='justify-content:right;'>"
            f"<div class='bubble-user'>{msg['text']}</div>"
            f"<img class='avatar-user' src='https://i.imgur.com/3XjA1Qp.png'>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='row' style='justify-content:left;'>"
            f"<img class='avatar-bot' src='https://i.imgur.com/6Z7N7wO.png'>"
            f"<div class='bubble-bot'>{msg['text']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if msg.get("image"):
            st.image(msg["image"], caption="Ảnh minh họa AI tạo")

# -----------------------------
# INPUT + BUTTON
# -----------------------------
user_input = st.text_input("Nhập câu hỏi…")

if st.button("Gửi") and user_input.strip() != "":
    st.session_state.history.append({"role": "user", "text": user_input})

    with st.spinner("AI đang trả lời…"):
        text = gen_text(user_input)
        img = gen_image(f"Hãy tạo ảnh minh họa rõ ràng, đẹp, đúng chủ đề: {user_input}")

    st.session_state.history.append({"role": "assistant", "text": text, "image": img})
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
