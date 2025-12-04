import streamlit as st
import requests
import time
import json
import base64
from io import BytesIO

# ==========================
# ⚙️ CẤU HÌNH API GEMINI
# ==========================

GEMINI_MODEL = "gemini-2.0-flash"

# Lấy API key từ st.secrets; hiển thị lỗi rõ nếu chưa cấu hình
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = None

if not API_KEY:
    st.error("⚠️ Vui lòng thêm `GEMINI_API_KEY` vào `.streamlit/secrets.toml` trước khi chạy ứng dụng.\n\n"
             "Ví dụ trong `.streamlit/secrets.toml`:\nGEMINI_API_KEY = \"YOUR_API_KEY_HERE\"")
    st.stop()

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"

SYSTEM_INSTRUCTION = (
    "Bạn là Gia sư ảo thân thiện và kiên nhẫn. Nhiệm vụ của bạn là giải đáp các câu hỏi "
    "về các môn học cho học sinh cấp 2 và cấp 3. Hãy: "
    "1. Đưa ra câu trả lời chi tiết, dễ hiểu, sử dụng LaTeX cho tất cả công thức toán học và phương trình hóa học. "
    "2. Nếu có hình ảnh, hãy phân tích hình ảnh trước khi trả lời. "
    "3. Giữ giọng điệu chuyên nghiệp nhưng khuyến khích học sinh đặt thêm câu hỏi."
)

# ==========================
# 🖼️ CHUYỂN ĐỔI HÌNH ẢNH BASE64
# ==========================

def get_base64_image(image_file):
    if image_file is None:
        return None
    return base64.b64encode(image_file.getvalue()).decode("utf-8")

# ==========================
# 🤖 HÀM GỌI API GEMINI
# ==========================

def get_gemini_response(prompt: str, image_data: str = None):
    # Dùng dict-style access để tránh StreamlitAPIException
    uploaded_file_info = st.session_state.get("uploaded_file")

    history_contents = []
    chat_history = st.session_state.get("chat_history", [])
    # Nếu history rỗng hoặc chỉ 1 phần tử, chat_history_for_api sẽ là []
    chat_history_for_api = chat_history[:-1] if len(chat_history) > 0 else []

    for message in chat_history_for_api:
        parts = []
        if "content" in message and message["content"]:
            parts.append({"text": message["content"]})
        if parts:
            history_contents.append({"role": message.get("role", "user"), "parts": parts})

    current_parts = []
    if image_data and uploaded_file_info:
        # đảm bảo uploaded_file_info có attribute 'type'
        mime = getattr(uploaded_file_info, "type", "image/jpeg")
        current_parts.append({
            "inlineData": {
                "mimeType": mime,
                "data": image_data
            }
        })

    if prompt:
        current_parts.append({"text": prompt})

    # Nếu không có parts gì cả, thêm một phần rỗng text để tránh payload rỗng
    if not current_parts:
        current_parts.append({"text": ""})

    payload = {
        "contents": history_contents + [{"role": "user", "parts": current_parts}],
        "systemInstruction": {"role": "system", "parts": [{"text": SYSTEM_INSTRUCTION}]}
    }

    max_retries = 3
    last_code = None

    for attempt in range(max_retries):
        try:
            res = requests.post(
                API_URL,
                headers={"Content-Type": "application/json"},
                json=payload
            )

            if res.status_code == 200:
                data = res.json()
                # Lấy text an toàn
                try:
                    text = (
                        data.get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", None)
                    )
                    if text:
                        return text
                except Exception:
                    pass

                # fallback: trả toàn bộ JSON tạm (nhỏ) nếu không có text
                return json.dumps(data)[:200] + "..."

            last_code = res.status_code
            # Nếu là xác thực thì break luôn (không retry nhiều)
            if last_code in (401, 403):
                break

            st.warning(f"Thử lại lần {attempt + 1}/{max_retries} thất bại. Mã: {last_code}")
            time.sleep(1.2 * (attempt + 1))

        except requests.RequestException as e:
            # lỗi kết nối mạng
            return f"❌ Lỗi kết nối API: {e}"
        except Exception as e:
            return f"❌ Lỗi không xác định khi gọi API: {e}"

    # Sau khi hết retry hoặc nhận 401/403
    if last_code in (401, 403):
        st.error(f"❌ Lỗi xác thực: mã {last_code}. Vui lòng kiểm tra API KEY và quyền truy cập model.")
    else:
        st.error(f"❌ Lỗi API nghiêm trọng: mã {last_code}")

    return "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau."

# ==========================
# 💾 QUẢN LÝ SESSION STATE
# ==========================

# Khởi tạo tất cả keys với dict-style để tránh set attribute sau khi session đã khởi tạo
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "user_info" not in st.session_state:
    st.session_state["user_info"] = {}

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "uploaded_file" not in st.session_state:
    st.session_state["uploaded_file"] = None

# ==========================
# 🔑 ĐĂNG NHẬP
# ==========================

def handle_login(name, class_name):
    if not name or not class_name:
        st.error("⚠️ Vui lòng nhập đầy đủ thông tin.")
        return

    st.session_state["user_info"] = {"name": name, "class": class_name}
    st.session_state["logged_in"] = True

    st.session_state["chat_history"] = [
        {"role": "assistant", "content": f"Chào bạn, **{name} (Lớp {class_name})**! Tôi là Gia sư ảo của bạn."}
    ]

    st.experimental_rerun()

# ==========================
# 💬 GỬI TIN NHẮN
# ==========================

def submit_chat():
    # lấy an toàn
    text = st.session_state.get("user_input", "")
    if text is None:
        text = ""
    text = text.strip()

    uploaded_file = st.session_state.get("uploaded_file")

    if not text and not uploaded_file:
        return

    image_base64 = None
    if uploaded_file:
        try:
            image_base64 = get_base64_image(uploaded_file)
            st.session_state["chat_history"].append({
                "role": "user",
                "content": f"Hình ảnh: {getattr(uploaded_file, 'name', 'uploaded_image')}",
                "image": uploaded_file
            })
        except Exception as e:
            st.error(f"Lỗi xử lý hình ảnh: {e}")
            return

    if text:
        st.session_state["chat_history"].append({"role": "user", "content": text})

    with st.spinner("⏳ Đang suy nghĩ..."):
        reply = get_gemini_response(text, image_base64)

    st.session_state["chat_history"].append({"role": "assistant", "content": reply})

    # reset uploader bằng dict-style
    st.session_state["uploaded_file"] = None

    # clear user_input nếu cần (form có clear_on_submit=True, nhưng an toàn vẫn clear)
    if "user_input" in st.session_state:
        st.session_state["user_input"] = ""

    st.experimental_rerun()

# ==========================
# 💻 GIAO DIỆN CHÍNH
# ==========================

st.set_page_config(page_title="Gia sư ảo", layout="centered")
st.title("👨‍🏫 Gia Sư Ảo — Đề Tài Nghiên Cứu Khoa Học")
st.markdown("---")


def show_login():
    st.subheader("Đăng nhập để bắt đầu học")
    with st.form("login_form"):
        name = st.text_input("Họ và tên")
        class_name = st.text_input("Lớp học")
        if st.form_submit_button("Bắt đầu"):
            handle_login(name, class_name)


def show_chat():
    user = st.session_state.get("user_info", {"name": "Học sinh", "class": ""})
    st.subheader(f"Xin chào, {user.get('name')} (Lớp {user.get('class')}) ✨")
    st.markdown("---")

    if st.button("Đăng xuất", type="primary"):
        st.session_state["logged_in"] = False
        st.session_state["chat_history"] = []
        st.experimental_rerun()

    # Hiển thị lịch sử chat
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.get("chat_history", []):
            with st.chat_message(msg.get("role", "user")):
                if "image" in msg:
                    try:
                        st.image(msg["image"], caption=msg.get("content", ""), width=220)
                    except Exception:
                        # Nếu bị lỗi hiển thị ảnh thì vẫn show nội dung text
                        st.write(msg.get("content", ""))
                else:
                    st.write(msg.get("content", ""))

    # File uploader (key = uploaded_file)
    st.file_uploader("Tải ảnh bài tập (tùy chọn)", type=["png", "jpg", "jpeg"], key="uploaded_file")

    # Form nhập chat
    with st.form("chat_form", clear_on_submit=True):
        st.text_input("Nhập câu hỏi", key="user_input", placeholder="Ví dụ: Giải phương trình...")
        if st.form_submit_button("Gửi", type="primary"):
            submit_chat()


if not st.session_state.get("logged_in", False):
    show_login()
else:
    show_chat()
