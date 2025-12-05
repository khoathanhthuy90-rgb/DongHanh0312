import streamlit as st
import requests
import base64

# ==========================
# ⚙️ CẤU HÌNH API GEMINI
# ==========================
GEMINI_MODEL = "gemini-2.0-flash"

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = None

if not API_KEY:
    st.error("⚠️ Vui lòng thêm GEMINI_API_KEY vào .streamlit/secrets.toml")
    st.stop()

API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={API_KEY}"
)

SYSTEM_INSTRUCTION = (
    "Bạn là Gia sư ảo thân thiện và kiên nhẫn. "
    "Hãy giải bài cho học sinh cấp 2–3. "
    "Trình bày dễ hiểu, dùng LaTeX cho công thức khi cần."
)

# ==========================
# >>>>> THÊM MỚI: HÌNH MINH HỌA <<<<<
# ==========================
IMAGE_LIBRARY = {
    "vật lý": [
        "https://upload.wikimedia.org/wikipedia/commons/0/02/Free-body-diagram.png",
        "https://upload.wikimedia.org/wikipedia/commons/0/07/Inclined_plane.png",
    ],
    "chuyển động": [
        "https://upload.wikimedia.org/wikipedia/commons/6/6e/Velocity_Time_Graph.png"
    ],
    "toán": [
        "https://upload.wikimedia.org/wikipedia/commons/3/3f/Right_triangle_definitions.svg",
        "https://upload.wikimedia.org/wikipedia/commons/2/2d/Linear_function_graph.png",
    ],
    "hóa học": [
        "https://upload.wikimedia.org/wikipedia/commons/3/33/Periodic_table_large.png"
    ],
    "thực tế": [
        "https://upload.wikimedia.org/wikipedia/commons/0/0c/Word_problem.png"
    ],
}

def find_related_image(user_text: str):
    """Tự tìm ảnh minh họa phù hợp theo từ khóa."""
    text = user_text.lower()

    for keyword, img_list in IMAGE_LIBRARY.items():
        if keyword in text:
            return img_list[0]  # lấy ảnh đầu tiên

    return None

# ==========================
# 🖼️ CONVERT ẢNH BASE64
# ==========================
def get_base64_image(image_file):
    if image_file is None:
        return None
    return base64.b64encode(image_file.getvalue()).decode("utf-8")

# ==========================
# 🤖 GỌI API GEMINI
# ==========================
def get_gemini_response(prompt: str, image_data: str = None):
    chat_history = st.session_state.get("chat_history", [])

    # Lịch sử hội thoại
    history_contents = []
    for msg in chat_history:
        history_contents.append({
            "role": msg["role"],
            "parts": [{"text": msg["content"]}]
        })

    # Tin nhắn hiện tại
    parts = []
    uploaded_file_obj = st.session_state.get("uploaded_file")

    if image_data and uploaded_file_obj:
        mime = getattr(uploaded_file_obj, "type", "image/jpeg")
        parts.append({
            "inlineData": {"mimeType": mime, "data": image_data}
        })

    # >>>>> THÊM MỚI: CHÈN LINK HÌNH MINH HỌA <<<<<
    suggest_img = find_related_image(prompt)
    if suggest_img:
        parts.append({"text": f"Hình minh họa: {suggest_img}"})

    if prompt:
        parts.append({"text": prompt})

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            }
        ] + history_contents + [
            {
                "role": "user",
                "parts": parts
            }
        ]
    }

    try:
        res = requests.post(
            API_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=45,
        )
    except Exception as e:
        return f"❌ Lỗi kết nối API: {e}"

    if res.status_code != 200:
        return f"❌ Lỗi API: mã {res.status_code}. Nội dung: {res.text[:300]}"

    data = res.json()

    return (
        data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
    )

# ==========================
# 💾 SESSION STATE
# ==========================
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user_info", {})
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("uploaded_file_widget", None)
st.session_state.setdefault("uploaded_file", None)
st.session_state.setdefault("user_input", "")
st.session_state.setdefault("should_reset_input", False)

if st.session_state["should_reset_input"]:
    st.session_state["user_input"] = ""
    st.session_state["uploaded_file"] = None
    st.session_state["should_reset_input"] = False


# ==========================
# 🔑 ĐĂNG NHẬP
# ==========================
def handle_login(name, class_name):
    if not name or not class_name:
        st.error("⚠️ Vui lòng nhập đầy đủ thông tin.")
        return
    st.session_state["logged_in"] = True
    st.session_state["user_info"] = {"name": name, "class": class_name}
    st.session_state["chat_history"] = [
        {"role": "assistant", "content": f"Chào {name} (Lớp {class_name})! Mình là Gia sư ảo 👨‍🏫"}
    ]


# ==========================
# 💬 GỬI TIN NHẮN
# ==========================
def submit_chat():
    text = st.session_state["user_input"].strip()
    widget_file = st.session_state["uploaded_file_widget"]

    if not text and not widget_file:
        return

    image_base64 = None
    if widget_file:
        image_base64 = get_base64_image(widget_file)
        st.session_state["uploaded_file"] = widget_file

        st.session_state["chat_history"].append({
            "role": "user",
            "content": f"(Đã gửi hình: {widget_file.name})"
        })

    if text:
        st.session_state["chat_history"].append({
            "role": "user",
            "content": text
        })

    with st.spinner("⏳ Đang phân tích..."):
        reply = get_gemini_response(text, image_base64)

    st.session_state["chat_history"].append({
        "role": "assistant",
        "content": reply
    })

    st.session_state["should_reset_input"] = True


# ==========================
# 🎨 UI
# ==========================
st.set_page_config(page_title="Gia sư ảo", layout="centered")

st.markdown("""
<style>
.chat-bubble-user {
    background: #DCF8C6;
    padding: 10px 15px;
    border-radius: 12px;
    margin: 6px 0;
    max-width: 80%;
}
.chat-bubble-bot {
    background: #F1F0F0;
    padding: 10px 15px;
    border-radius: 12px;
    margin: 6px 0;
    max-width: 80%;
}
</style>
""", unsafe_allow_html=True)


def show_login():
    st.title("👨‍🏫 Gia Sư Ảo – Đề tài NCKH")
    st.subheader("Đăng nhập để bắt đầu học")

    with st.form("login_form"):
        name = st.text_input("Họ và tên")
        class_name = st.text_input("Lớp học")

        if st.form_submit_button("Bắt đầu"):
            handle_login(name, class_name)


def show_chat():
    user = st.session_state["user_info"]
    st.title(f"✨ Xin chào {user['name']} – Lớp {user['class']} ✨")

    if st.button("🚪 Đăng xuất"):
        st.session_state["logged_in"] = False
        st.session_state["chat_history"] = []
        return

    st.markdown("---")

    # Lịch sử chat
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-bubble-bot'>{msg['content']}</div>", unsafe_allow_html=True)

    # Upload ảnh
    st.file_uploader(
        "📷 Tải ảnh bài tập (tùy chọn)",
        type=["png", "jpg", "jpeg"],
        key="uploaded_file_widget"
    )

    # Form chat
    with st.form("chat_form", clear_on_submit=True):
        st.text_input("Nhập câu hỏi…", key="user_input")
        if st.form_submit_button("Gửi"):
            submit_chat()


# ==========================
# 🚀 RUN APP
# ==========================
if not st.session_state["logged_in"]:
    show_login()
else:
    show_chat()
