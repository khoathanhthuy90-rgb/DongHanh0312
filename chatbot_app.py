# app_gia_su_ao_final_stable.py
import streamlit as st
import requests, base64, uuid, io
from datetime import datetime

# --------------------------
# CONFIG
# --------------------------
API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
if not API_KEY:
    st.error("⚠️ Thiếu GEMINI_API_KEY trong .streamlit/secrets.toml. Vui lòng kiểm tra lại cấu hình.")
    st.stop()

MODEL_OPTIONS = {
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
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
# SESSION INIT
# --------------------------
for key in ["chat_history", "image_history", "chosen_model"]:
    if key not in st.session_state:
        st.session_state[key] = []
        
for key in ["user_name", "user_class", "user_input_area", "pending_action", "temp_question", "tts_enabled", "style"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key not in ["tts_enabled"] else False

# --------------------------
# HELPERS
# --------------------------
def call_gemini_text(model, user_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    user_name = st.session_state.get("user_name", "học sinh")
    user_class = st.session_state.get("user_class", "Chưa rõ")
    personal_context = (
        f"Bạn đang nói chuyện với học sinh tên là {user_name} (Lớp {user_class}). "
        "Hãy luôn thân thiện, vui vẻ, và nhắc tên học sinh tự nhiên."
    )
    full_prompt = f"{SYSTEM_INSTRUCTION} {personal_context}\n\n[Đề bài]: {user_prompt}"
    payload = {"contents": [{"role":"user", "parts":[{"text": full_prompt}]}]}
    try:
        res = requests.post(url, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text, None
    except Exception as e:
        error_detail = res.text if 'res' in locals() else str(e)
        return None, f"Lỗi API văn bản: {error_detail}"

def call_gemini_image(model, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {"contents":[{"role":"user","parts":[{"text": prompt}]}]}
    try:
        res = requests.post(url, json=payload, timeout=90)
        res.raise_for_status()
        data = res.json()
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []): 
                if "inlineData" in part and part["inlineData"]["mimeType"].startswith("image/"):
                    return part["inlineData"]["data"], None
        return None, "Không tìm thấy media (ảnh) trong phản hồi."
    except Exception as e:
        error_detail = res.text if 'res' in locals() else str(e)
        return None, f"Lỗi API ảnh: {error_detail}"

def store_image_entry(question_text, img_b64, style_key):
    img_id = str(uuid.uuid4())
    st.session_state.image_history.append({
        "id": img_id, "question": question_text,
        "b64": img_b64, "style": style_key,
        "time": datetime.utcnow().isoformat()
    })
    return img_id

def speak_text(text):
    try:
        from gtts import gTTS
        fp = io.BytesIO()
        clean_text = text.replace("**","").replace("$","").replace("\\","").replace("{","").replace("}","")
        tts = gTTS(text=clean_text, lang="vi")
        tts.write_to_fp(fp)
        fp.seek(0)
        st.audio(fp.read(), format="audio/mp3")
    except Exception:
        st.warning("Không thể tạo giọng nói.")

def set_pending_action(action_type):
    q = st.session_state.user_input_area.strip()
    if not q: return
    st.session_state["temp_question"] = q
    st.session_state.user_input_area = "" 
    st.session_state["pending_action"] = action_type

# --------------------------
# LOGIN INTERFACE (HIỆU ỨNG)
# --------------------------
if not st.session_state.user_name or not st.session_state.user_class:
    st.markdown("""
        <style>
        .login-title {font-size: 36px; color:#2c3e50; background:white; display:inline-block; padding:8px 15px; border-radius:8px; margin:10px; text-shadow:2px 2px 5px rgba(0,0,0,0.3); animation: fadeIn 1.5s ease-in-out;}
        .login-subtitle {font-size: 24px; color:#34495e; margin:10px; animation: fadeIn 2s ease-in-out;}
        .login-desc {font-size: 18px; color:#2c3e50; margin-top:5px; animation: fadeIn 2.5s ease-in-out;}
        @keyframes fadeIn {from {opacity:0; transform:translateY(-20px);} to {opacity:1; transform:translateY(0);}}
        </style>
        <div style="text-align:center; background: linear-gradient(to right,#a1c4fd,#c2e9fb); padding:40px; border-radius:12px; margin-bottom:20px;">
            <div style="font-size:100px; margin-bottom:15px;">🤖</div>
            <h1 class='login-title'>GIA SƯ ẢO CỦA BẠN</h1>
            <h3 class='login-subtitle'>ĐỀ TÀI NGHIÊN CỨU KHOA HỌC</h3>
            <p class='login-desc'>Nhập Họ và Tên cùng Lớp để bắt đầu trải nghiệm</p>
        </div>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns([1,1])
    with col1:
        name_input = st.text_input("Họ và tên", value=st.session_state.user_name)
    with col2:
        class_input = st.text_input("Lớp", value=st.session_state.user_class)
    if st.button("Đăng nhập", use_container_width=True):
        if name_input.strip() and class_input.strip():
            st.session_state.user_name = name_input.strip()
            st.session_state.user_class = class_input.strip()
            st.rerun()
        else:
            st.warning("Vui lòng nhập đủ Họ tên và Lớp.")
    st.stop()

# --------------------------
# SIDEBAR
# --------------------------
with st.sidebar:
    st.markdown(f"### Xin chào, **{st.session_state.user_name}** - Lớp **{st.session_state.user_class}**")
    chosen_label = st.selectbox("Chọn model Gemini", list(MODEL_OPTIONS.keys()))
    st.session_state.chosen_model = MODEL_OPTIONS[chosen_label]
    style = st.selectbox("Phong cách ảnh", list(STYLE_PROMPT_MAP.keys()), index=0)
    tts_enabled = st.checkbox("Bật Text-to-Speech (Đọc lời giải)", value=st.session_state.get("tts_enabled", False))
    st.session_state["tts_enabled"] = tts_enabled 
    st.session_state["style"] = style 

# --------------------------
# MAIN UI
# --------------------------
with st.container():
    col_left, col_right = st.columns([3, 1]) 
    with col_right:
        st.subheader("📂 Nhật ký ảnh")
        for entry in reversed(st.session_state.image_history[-6:]):
            try:
                st.image(base64.b64decode(entry["b64"]), width=100)
            except Exception:
                st.caption("❌ Ảnh lỗi")
            st.caption(f"📝 {entry['question'][:30]}...")

    with col_left:
        st.markdown("<style> .chat-box {max-height:600px; overflow-y:auto; padding:10px;} </style>", unsafe_allow_html=True) 
        chat_container = st.container()
        def show_chat():
            with chat_container:
                for msg in st.session_state.chat_history: 
                    role = msg["role"]
                    color = "#e6f3ff" if role=="user" else "#f0e6ff"
                    st.markdown(f"""
                    <div style='background:{color}; padding:12px; border-radius:10px; margin-bottom:8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                        {msg['text']}
                    </div>""", unsafe_allow_html=True)
                    if msg.get("image_b64"):
                        try:
                            st.image(base64.b64decode(msg["image_b64"]), use_column_width=True)
                        except Exception:
                            st.error("Lỗi hiển thị ảnh.")
        show_chat()

# --------------------------
# API PROCESSING
# --------------------------
if st.session_state.get("pending_action"):
    q = st.session_state.get("temp_question")
    if st.session_state["pending_action"] == "text":
        st.session_state.chat_history.append({"role":"user","text":q,"time":datetime.utcnow().isoformat()})
        with st.spinner("⏳ Đang tạo lời giải..."):
            answer, err = call_gemini_text(st.session_state.chosen_model, q)
            if err:
                st.session_state.chat_history.append({"role":"assistant","text":f"❌ Lỗi: {err}","time":datetime.utcnow().isoformat()})
            else:
                st.session_state.chat_history.append({"role":"assistant","text":answer,"time":datetime.utcnow().isoformat()})
                if st.session_state.get("tts_enabled"): speak_text(answer) 
    elif st.session_state["pending_action"] == "image":
        st.session_state.chat_history.append({"role":"user","text":f"[Yêu cầu tạo ảnh]: {q}","time":datetime.utcnow().isoformat()})
        with st.spinner("🎨 Đang tạo ảnh minh họa..."):
            style_key = st.session_state.get("style", "Gia sư trẻ trung") 
            img_b64, img_err = call_gemini_image(st.session_state.chosen_model, f"{q} - style: {style_key}")
            if img_err:
                st.session_state.chat_history.append({"role":"assistant","text":f"❌ Lỗi tạo ảnh từ API: {img_err}","time":datetime.utcnow().isoformat()})
            elif not img_b64:
                 st.session_state.chat_history.append({"role":"assistant","text":"❌ Lỗi: API không trả về dữ liệu ảnh hợp lệ.","time":datetime.utcnow().isoformat()})
            else:
                st.session_state.chat_history.append({
                    "role":"assistant","text":"**[Ảnh minh họa đã tạo]**","image_b64":img_b64,
                    "time":datetime.utcnow().isoformat()
                })
                store_image_entry(q, img_b64, style_key)
    st.session_state["pending_action"] = ""
    st.session_state["temp_question"] = ""
    st.rerun()

# --------------------------
# USER INPUT
# --------------------------
user_q = st.text_area("Nhập câu hỏi của bạn:", height=120, key="user_input_area") 
col1_btn, col2_btn = st.columns([1,1])
with col1_btn:
    st.button("Gửi câu hỏi", use_container_width=True, type="primary", on_click=set_pending_action, args=("text",))
with col2_btn:
    st.button("Tạo ảnh minh họa", use_container_width=True, on_click=set_pending_action, args=("image",))
