# app_gia_su_ao_v6.py (Phiên bản đã sửa lỗi API, giữ nguyên tính năng)
import streamlit as st
import requests, base64, uuid, io
from datetime import datetime

# --------------------------
# CONFIG
# --------------------------
API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
if not API_KEY:
    st.error("⚠️ Thiếu GEMINI_API_KEY trong .streamlit/secrets.toml")
    st.stop()

# Đã cập nhật tên mô hình chuẩn của Gemini
MODEL_OPTIONS = {
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 2.5 Pro": "gemini-2.5-pro", 
    # Tên mô hình cũ "Gemini 2.0 Pro" đã được thay bằng "Gemini 2.5 Pro"
}

SYSTEM_INSTRUCTION = (
    "Bạn là gia sư ảo thân thiện, giải bài cho học sinh cấp 2–3. "
    "Trình bày rõ ràng, dùng LaTeX khi cần."
)

STYLE_PROMPT_MAP = {
    "Gia sư trẻ trung": "young friendly tutor, smiling, colorful, modern, cartoon-realistic style"
}

st.set_page_config(page_title="Gia Sư Ảo", layout="wide", page_icon="🤖")

# --------------------------
# SESSION INIT (Giữ nguyên)
# --------------------------
for key in ["chat_history","image_history","user_input","chosen_model","user_name","user_class"]:
    if key not in st.session_state:
        st.session_state[key] = "" if "input" in key or "name" in key or "class" in key else []

# --------------------------
# LOGIN (Giữ nguyên)
# --------------------------
if not st.session_state.user_name or not st.session_state.user_class:
    st.markdown("""
        <div style="text-align:center; background: linear-gradient(to right, #74ebd5, #ACB6E5); padding:30px; border-radius:12px; margin-bottom:20px;">
            <img src="https://i.imgur.com/4AiXzf8.png" width="120" style="border-radius:50%;"/>
            <h1 style='color:#2c3e50; margin:10px;'>👨‍🏫 GIA SƯ ẢO CỦA BẠN</h1>
            <h4 style='color:#7f8c8d; margin:5px;'>ĐỀ TÀI NGHIÊN CỨU KHOA HỌC</h4>
        </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns([1,1])
    with col1: name_input = st.text_input("Họ và tên")
    with col2: class_input = st.text_input("Lớp")
    if st.button("Đăng nhập", use_container_width=True):
        if name_input.strip() and class_input.strip():
            st.session_state.user_name = name_input.strip()
            st.session_state.user_class = class_input.strip()
            # Dùng rerun để cập nhật giao diện sau khi đăng nhập
            st.rerun() 
        else:
            st.warning("Vui lòng nhập đủ Họ tên và Lớp.")
    st.stop()

# --------------------------
# HELPERS (Đã sửa lỗi API)
# --------------------------
def call_gemini_text(model, user_prompt):
    """ SỬA LỖI: Gọi Gemini dùng endpoint generateContent chuẩn """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    
    # Cấu trúc Payload chuẩn cho generateContent
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ],
        "config": {
            "systemInstruction": SYSTEM_INSTRUCTION,
            "temperature": 0.2,
            "maxOutputTokens": 2048 # Tăng max tokens để có lời giải chi tiết hơn
        }
    }
    try:
        res = requests.post(url, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        
        # SỬA LỖI: Lấy nội dung từ response chuẩn của generateContent
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text, None
    except Exception as e:
        error_detail = res.text if 'res' in locals() else str(e)
        return None, f"Lỗi API văn bản: {error_detail}"

def call_gemini_image(model, prompt):
    """ SỬA LỖI: Gọi Gemini để tạo ảnh (dù cần API Imagen/Multimodal riêng) """
    # LƯU Ý: Chức năng tạo ảnh thực tế cần model Imagen/Gemini Multimodal có trả về media.
    # Logic code vẫn được sửa để tuân thủ cú pháp generateContent.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    
    # Cấu trúc Payload chuẩn cho generateContent
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "config": {
            "temperature": 0.2,
        }
    }
    
    try:
        res = requests.post(url, json=payload, timeout=90)
        res.raise_for_status()
        data = res.json()
        
        # SỬA LỖI: Tìm media (ảnh base64) trong response chuẩn của generateContent
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                # 'inlineData' chứa base64 image data
                if "inlineData" in part and part["inlineData"]["mimeType"].startswith("image/"):
                    return part["inlineData"]["data"], None
        
        # Thêm thông báo nếu không tìm thấy ảnh
        return None, "Không tìm thấy media (ảnh) trong phản hồi. Hãy kiểm tra xem mô hình có hỗ trợ tạo ảnh không."
    except Exception as e:
        error_detail = res.text if 'res' in locals() else str(e)
        return None, f"Lỗi API ảnh: {error_detail}"

def store_image_entry(question_text, img_b64, style_key):
    img_id = str(uuid.uuid4())
    st.session_state.image_history.append({
        "id": img_id, "question": question_text, "b64": img_b64, "style": style_key,
        "time": datetime.utcnow().isoformat()
    })
    return img_id

def speak_text(text):
    try:
        from gtts import gTTS
        fp = io.BytesIO()
        # Loại bỏ các ký tự có thể gây lỗi đọc
        clean_text = text.replace("**", "").replace("$", "").replace("\\", "")
        tts = gTTS(text=clean_text, lang="vi")
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp.read(), format="audio/mp3")
    except ImportError:
        st.error("Lỗi: Thiếu thư viện gTTS. Vui lòng chạy: `pip install gTTS`")
    except Exception as e:
        st.warning("Không thể tạo giọng nói: " + str(e))

# --------------------------
# SIDEBAR (Giữ nguyên)
# --------------------------
with st.sidebar:
    st.markdown(f"### Xin chào, {st.session_state.user_name} - Lớp {st.session_state.user_class}")
    # Đã cập nhật danh sách keys
    chosen_label = st.selectbox("Chọn model Gemini", list(MODEL_OPTIONS.keys()))
    st.session_state.chosen_model = MODEL_OPTIONS[chosen_label]
    style = st.selectbox("Phong cách ảnh", list(STYLE_PROMPT_MAP.keys()), index=0)
    tts_enabled = st.checkbox("Bật Text-to-Speech", value=False)

# --------------------------
# MAIN UI (Giữ nguyên)
# --------------------------
col_left, col_right = st.columns([3,2])
with col_left:
    st.subheader("Nhập đề bài / câu hỏi")
    user_q = st.text_area("", value=st.session_state.get("user_input",""), height=150)
    st.session_state.user_input = user_q

    btn_send = st.button("Gửi câu hỏi")
    btn_image = st.button("Tạo ảnh minh họa")

    chat_container = st.empty()
    # Hàm show_chat được sửa để dùng st.chat_message cho giao diện đẹp hơn nhưng vẫn giữ cấu trúc cũ
    def show_chat():
        with chat_container.container():
            # Thay thế đoạn CSS thủ công bằng st.chat_message
            for m in st.session_state.chat_history:
                role = m["role"]
                with st.chat_message(role):
                    st.markdown(m['text'])
                    
                    if m.get("image_b64"):
                        st.image(base64.b64decode(m["image_b64"]), use_column_width=True)
                        st.download_button("📥 Tải ảnh", data=base64.b64decode(m["image_b64"]),
                                        file_name=f"minh_hoa_{uuid.uuid4().hex[:6]}.png", mime="image/png")
    show_chat()

# --------------------------
# ACTION: Gửi câu hỏi (Đã thêm st.rerun)
# --------------------------
if btn_send and user_q.strip():
    st.session_state.chat_history.append({"role":"user","text":user_q,"time":datetime.utcnow().isoformat()})
    
    with st.spinner("⏳ Đang tạo lời giải..."):
        answer_text, err = call_gemini_text(st.session_state.chosen_model, user_q)
        if err: 
            st.error(err)
            st.session_state.chat_history.append({"role":"assistant","text":f"❌ Lỗi: {err}","time":datetime.utcnow().isoformat()})
        else:
            st.session_state.chat_history.append({"role":"assistant","text":answer_text,"time":datetime.utcnow().isoformat()})
            if tts_enabled: speak_text(answer_text)
    
    # Dùng rerun để cập nhật toàn bộ giao diện chat và xóa input
    st.session_state.user_input = "" 
    st.rerun()

# --------------------------
# ACTION: Tạo ảnh minh họa (Đã thêm st.rerun)
# --------------------------
if btn_image and user_q.strip():
    img_prompt = f"Educational illustration with style '{style}': {user_q}."
    
    # Ghi lại yêu cầu tạo ảnh
    st.session_state.chat_history.append({"role":"user","text":f"[Yêu cầu tạo ảnh]: {user_q}","time":datetime.utcnow().isoformat()})
    
    with st.spinner("🎨 Đang tạo ảnh minh họa..."):
        img_b64, img_err = call_gemini_image(st.session_state.chosen_model, img_prompt)
        if img_err: 
            st.error("Không tạo được ảnh: " + img_err)
            st.session_state.chat_history.append({"role":"assistant", "text": f"❌ Lỗi tạo ảnh: {img_err}"})
        else:
            st.session_state.chat_history.append({
                "role":"assistant",
                "text":"**[Ảnh minh họa đã tạo]**",
                "image_b64": img_b64,
                "time": datetime.utcnow().isoformat()
            })
            store_image_entry(user_q, img_b64, style)
            
    # Dùng rerun để cập nhật toàn bộ giao diện chat và xóa input
    st.session_state.user_input = "" 
    st.rerun()

with col_right:
    st.subheader("📂 Nhật ký ảnh")
    # Giữ nguyên logic hiển thị ảnh ở cột phải
    for entry in reversed(st.session_state.image_history[-6:]):
        st.image(base64.b64decode(entry["b64"]), width=160)
        st.write(f"📝 {entry['question'][:50]}...")
