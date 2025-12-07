import streamlit as st
import requests
import json

# ============================================
# PHẦN LẤY API KEYS
# ============================================
GEMINI_KEYS = st.secrets.get("GEMINI_KEYS", [])
if not GEMINI_KEYS:
    st.error("⚠️ Bạn chưa cấu hình GEMINI_KEYS trong secrets.toml")
    st.stop()

MODEL_MAIN = st.secrets.get("MODEL", "gemini-2.5-flash")
MODEL_FALLBACK = st.secrets.get("FALLBACK_MODEL", "gemini-1.5-flash")

# ============================================
# HÀM GỌI API CÓ TỰ ĐỘNG XOAY API KEY
# ============================================
def call_gemini_api(model, payload):
    last_error = None

    for key in GEMINI_KEYS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            res = requests.post(url, json=payload, timeout=60)

            # Nếu quá quota → thử key khác
            if res.status_code == 429:
                last_error = "429 - Hết quota, chuyển key khác..."
                continue

            res.raise_for_status()
            return res.json()  # thành công

        except Exception as e:
            last_error = str(e)
            continue

    return None, last_error

# ============================================
# HÀM TỔNG HỢP — TỰ CHUYỂN MODEL NẾU MODEL CHÍNH HẾT QUOTA
# ============================================
def generate_text(prompt):
    payload = {
        "contents":[
            {"role":"user",
             "parts":[{"text": prompt}]}
        ]
    }

    # 1) Thử model chính trước
    data = call_gemini_api(MODEL_MAIN, payload)
    if data[0]:
        return data[0]
    else:
        st.warning("⚠️ Model chính hết quota → thử model fallback...")

    # 2) Nếu model chính hỏng → chuyển sang fallback model
    data2 = call_gemini_api(MODEL_FALLBACK, payload)
    if data2[0]:
        return data2[0]

    # 3) Cả hai đều lỗi
    return None

# ============================================
# GIAO DIỆN STREAMLIT
# ============================================
st.title("🚀 Gemini API — Auto Key Rotation (Fixed Quota Error)")
prompt = st.text_input("Nhập câu hỏi:")

if st.button("Gửi"):
    if not prompt.strip():
        st.warning("Bạn chưa nhập nội dung.")
        st.stop()

    with st.spinner("⏳ Đang xử lý..."):
        result = generate_text(prompt)

        if not result:
            st.error("❌ Fallback thất bại. Tất cả API key đều hết quota hoặc bị lỗi.")
        else:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            st.success("✔ Thành công!")
            st.write(text)
