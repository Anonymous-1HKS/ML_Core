from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import PIL.Image
import io
import sys
import contextlib
import PyPDF2
import traceback

app = Flask(__name__)
CORS(app)

# ==========================================
# ⚠️ DÁN API KEY CỦA BẠN VÀO ĐÂY
# ==========================================
GOOGLE_API_KEY = "Gemini"
genai.configure(api_key=GOOGLE_API_KEY)

model_chat = genai.GenerativeModel('gemini-2.5-flash')
model_code = genai.GenerativeModel('gemini-2.5-flash', generation_config={"temperature": 0.2})
chat_session = model_chat.start_chat(history=[])

# === SỬA LỖI RELOAD: DÙNG RAM THAY VÌ FILE ===
# Lưu lịch sử vào biến này (Tắt server sẽ mất, nhưng web không bị reload)
RAM_HISTORY = []

# --- HÀM THỰC THI CODE ---
def execute_python_code(code):
    output_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, {})
        return output_buffer.getvalue()
    except Exception as e:
        return f"Traceback:\n{str(e)}"

def extract_text_from_pdf(file_stream):
    try:
        reader = PyPDF2.PdfReader(file_stream)
        text = "".join([p.extract_text() for p in reader.pages])
        return text
    except Exception as e:
        return str(e)

@app.route('/api/login', methods=['POST'])
def login():
    return jsonify({"status": "success", "name": "Admin VisionOS", "message": "Login OK"})

@app.route('/api/execute', methods=['POST'])
def execute_code():
    try:
        data = request.json
        lang = data.get('lang', 'web')
        code = data.get('code', '')
        if lang == 'python':
            return jsonify({"output": execute_python_code(code)})
        return jsonify({"output": "⚠️ Chỉ hỗ trợ chạy Python trên server."})
    except Exception as e:
        return jsonify({"output": str(e)})

@app.route('/api/code', methods=['POST'])
def ai_code():
    try:
        data = request.json
        mode = data.get('mode', 'explain')
        code_content = data.get('code', '')
        user_prompt = data.get('prompt', '')
        lang = data.get('lang', 'python')

        if mode == 'fix': prompt = f"Tìm lỗi và sửa code {lang} này:\n{code_content}"
        elif mode == 'suggest': prompt = f"Viết code {lang}: {user_prompt}"
        else: prompt = f"Giải thích code {lang}:\n{code_content}"

        response = model_code.generate_content(prompt)
        clean_reply = response.text.replace("```python", "").replace("```html", "").replace("```javascript", "").replace("```", "")
        return jsonify({"reply": clean_reply})
    except Exception as e:
        return jsonify({"reply": f"// Lỗi AI: {str(e)}"})

# === API CHAT (LƯU VÀO RAM) ===
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        reply_text = ""
        user_msg = ""

        # Xử lý File/Ảnh
        if 'file' in request.files:
            file = request.files['file']
            user_msg = request.form.get('message', 'Gửi file')
            filename = file.filename.lower()

            if filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                img = PIL.Image.open(file)
                response = model_chat.generate_content([user_msg, img])
            elif filename.endswith('.pdf'):
                pdf_text = extract_text_from_pdf(file)
                response = model_chat.generate_content(f"Tài liệu:\n{pdf_text}\n\nCâu hỏi: {user_msg}")
            else:
                return jsonify({"reply": "File không hỗ trợ."})

            reply_text = response.text

        # Xử lý Text
        elif request.is_json:
            data = request.json
            user_msg = data.get('message', '')
            response = chat_session.send_message(user_msg)
            reply_text = response.text

        # LƯU VÀO RAM (Không tạo file -> Không reload)
        RAM_HISTORY.append({"role": "user", "content": user_msg})
        RAM_HISTORY.append({"role": "ai", "content": reply_text})

        return jsonify({"reply": reply_text})

    except Exception as e:
        print("Lỗi:", e)
        return jsonify({"reply": f"⚠️ Lỗi: {str(e)}"})

@app.route('/api/history', methods=['GET'])
def get_history():
    return jsonify(RAM_HISTORY)

@app.route('/api/new_chat', methods=['POST'])
def new_chat():
    global chat_session
    chat_session = model_chat.start_chat(history=[])
    return jsonify({"status": "reset"})

@app.route('/api/delete', methods=['DELETE'])
def delete_all():
    global chat_session, RAM_HISTORY
    chat_session = model_chat.start_chat(history=[])
    RAM_HISTORY = [] # Xóa sạch RAM
    return jsonify({"status": "deleted"})

if __name__ == '__main__':
    # use_reloader=False RẤT QUAN TRỌNG
    app.run(debug=True, port=5000, use_reloader=False)