from flask import Flask, render_template_string, request
import requests
import uuid
import time

# ==============================
# CONFIG
# ==============================
GEMINI_MODEL = "gemini-2.5-flash-preview-09-2025"
API_KEY = ""   # <-- Điền API KEY vào đây
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={API_KEY}"

app = Flask(__name__)

# ==============================
# GEMINI API
# ==============================
def ask_gemini(prompt):
    if not API_KEY:
        return "Lỗi: Bạn chưa nhập API KEY."

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [{"text": "Bạn là Gia sư ảo thân thiện, giải thích chậm rãi, dễ hiểu."}]
        }
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=20)

        if response.status_code == 200:
            data = response.json()
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return f"Lỗi API: {response.status_code}"
    except Exception as e:
        return f"Lỗi khi gọi API: {e}"


# ==============================
# HTML TEMPLATE (GIAO DIỆN WEB)
# ==============================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8" />
    <title>Gia Sư Ảo Python</title>
    <style>
        body { font-family: Arial; background: #f3f3f3; padding: 20px; }
        .box { width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; }
        .msg-user { text-align: right; color: green; margin: 10px 0; }
        .msg-ai { text-align: left; color: #333; margin: 10px 0; }
        textarea { width: 100%; height: 80px; margin-top: 10px; }
        button { padding: 10px 20px; margin-top: 10px; background: green; color: white; border: none; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>💬 Gia Sư Ảo (Python Flask)</h2>
        <form method="POST">
            <label>Nhập câu hỏi:</label>
            <textarea name="message" required>{{user_input}}</textarea>
            <button type="submit">Gửi</button>
        </form>

        {% if user_message %}
            <p class="msg-user"><b>Bạn:</b> {{user_message}}</p>
        {% endif %}
        {% if ai_message %}
            <p class="msg-ai"><b>Gia sư ảo:</b> {{ai_message}}</p>
        {% endif %}
    </div>
</body>
</html>
"""


# ==============================
# ROUTES
# ==============================
@app.route("/", methods=["GET", "POST"])
def home():
    user_input = ""
    user_message = ""
    ai_message = ""

    if request.method == "POST":
        user_input = request.form.get("message", "")
        user_message = user_input
        ai_message = ask_gemini(user_input)

    return render_template_string(HTML,
                                  user_input=user_input,
                                  user_message=user_message,
                                  ai_message=ai_message)


# ==============================
# RUN APP
# ==============================
if __name__ == "__main__":
    print("🔥 Server chạy tại: http://127.0.0.1:5000")
    app.run(debug=True)
