import os
import io
import json
import uuid
import contextlib
import threading
import subprocess
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO
from PIL import Image
import numpy as np
import tensorflow as tf  # Import tensorflow as tf để sử dụng tf.keras

# ===== GEMINI CONFIG =====
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# API KEY
GOOGLE_API_KEY = "GOOGLE_API"

try:
   genai.configure(api_key=GOOGLE_API_KEY)
   model_chat = genai.GenerativeModel("gemini-2.5-flash")
   model_code = genai.GenerativeModel("gemini-2.5-flash", generation_config={"temperature": 0.2})
except Exception as e:
   print(f"Lỗi Config: {e}")

# Load kitchen model and classes (sử dụng path tương đối, giả sử file ở cùng thư mục với app.py)
try:
   kitchen_model = tf.keras.models.load_model('/Volumes/Programming/ML_Core/Kitchen_utensils_model.h5')
   with open('/Volumes/Programming/ML_Core/Utensils.txt', 'r') as f:
       kitchen_classes = [line.strip().split(' ', 1)[1] for line in f.readlines()]
except Exception as e:
   print(f"Lỗi load model: {e}")
   kitchen_model = None
   kitchen_classes = []

# ===== FLASK APP =====
app = Flask(__name__)
app.config["SECRET_KEY"] = "supml_final_key"
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

SESSION_FILE = "sessions.json"

# ===== CACHE RAM (Để chạy nhanh) =====
GLOBAL_SESSIONS = {}
if os.path.exists(SESSION_FILE):
   try:
       with open(SESSION_FILE, "r", encoding="utf-8") as f:
           GLOBAL_SESSIONS = json.load(f)
   except: GLOBAL_SESSIONS = {}

def save_sessions_background():
   try:
       with open(SESSION_FILE, "w", encoding="utf-8") as f:
           json.dump(GLOBAL_SESSIONS, f, ensure_ascii=False, indent=2)
   except: pass

# ===== ROUTE MỚI: PHỤC VỤ WEB TRỰC TIẾP =====
@app.route("/")
def index():
   # Code này sẽ mở file index.html và gửi cho trình duyệt
   # Giúp bạn không cần dùng Live Server nữa -> Hết lỗi reload
   return send_file("index.html")

# ===== API ROUTES =====
@app.route("/api/login", methods=["POST"])
def login(): return jsonify({"status": "success"})

@app.route("/api/sessions", methods=["GET"])
def get_sessions():
   summary = [{"id": k, "title": v["title"]} for k, v in GLOBAL_SESSIONS.items()]
   return jsonify(list(reversed(summary)))

@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
   if session_id in GLOBAL_SESSIONS:
       del GLOBAL_SESSIONS[session_id]
       threading.Thread(target=save_sessions_background).start()
   return jsonify({"status": "deleted"})

@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_content(session_id):
   return jsonify(GLOBAL_SESSIONS.get(session_id, {}).get("messages", []))

@app.route("/api/delete_all", methods=["DELETE"])
def delete_all():
   global GLOBAL_SESSIONS
   GLOBAL_SESSIONS = {}
   if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
   return jsonify({"status": "ok"})

@app.route("/api/chat", methods=["POST"])
def chat():
   try:
       json_data = request.get_json(silent=True) or {}
       session_id = request.form.get("session_id") or json_data.get("session_id")
       user_msg = request.form.get("message") or json_data.get("message") or ""

       if not session_id or session_id not in GLOBAL_SESSIONS:
           session_id = str(uuid.uuid4())
           GLOBAL_SESSIONS[session_id] = {"title": "New Chat", "messages": []}

       inputs = [user_msg]
       if 'file' in request.files:
           file = request.files['file']
           if file.filename != '':
               img = Image.open(io.BytesIO(file.read()))
               inputs.append(img)

       response = model_chat.generate_content(inputs)
       reply_text = response.text

       if len(GLOBAL_SESSIONS[session_id]["messages"]) == 0:
           GLOBAL_SESSIONS[session_id]["title"] = user_msg[:30] if user_msg else "Image Chat"

       user_id = str(uuid.uuid4())
       GLOBAL_SESSIONS[session_id]["messages"].append({"id": user_id, "role": "user", "content": user_msg})
       ai_id = str(uuid.uuid4())
       GLOBAL_SESSIONS[session_id]["messages"].append({"id": ai_id, "role": "ai", "content": reply_text})

       threading.Thread(target=save_sessions_background).start()

       return jsonify({"reply": reply_text, "session_id": session_id, "user_msg_id": user_id})
   except Exception as e:
       return jsonify({"reply": f"Lỗi: {e}", "session_id": session_id})

@app.route("/api/predict", methods=["POST"])
def predict():
   if "file" not in request.files: return jsonify({"error": "No file"})
   try:
       file = request.files["file"]
       img = Image.open(io.BytesIO(file.read()))
       res = model_chat.generate_content(["Đây là gì? Trả lời ngắn.", img])
       return jsonify({"label": res.text.strip(), "confidence": 99.0})
   except: return jsonify({"label": "Lỗi", "confidence": 0})

@app.route("/api/code", methods=["POST"])
def gen_code():
   d = request.json
   try:
       res = model_code.generate_content(f"{d.get('mode')} code {d.get('lang')}: {d.get('code')}")
       return jsonify({"reply": res.text.replace("```", "")})
   except: return jsonify({"reply": "Error"})

@app.route("/api/execute", methods=["POST"])
def exec_code():
   lang = request.json.get("lang", "python")
   code = request.json.get("code", "")
   if lang == "python":
       try:
           buf = io.StringIO()
           with contextlib.redirect_stdout(buf): exec(code, {})
           return jsonify({"output": buf.getvalue()})
       except Exception as e: return jsonify({"error": str(e)})
   elif lang in ["c", "cpp"]:
       suffix = ".c" if lang == "c" else ".cpp"
       compiler = "gcc" if lang == "c" else "g++"
       with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
           f.write(code.encode('utf-8'))
           f_name = f.name
       out_name = f_name + ".out"
       compile_cmd = [compiler, f_name, "-o", out_name]
       try:
           compile_output = subprocess.check_output(compile_cmd, stderr=subprocess.STDOUT)
       except subprocess.CalledProcessError as e:
           os.unlink(f_name)
           return jsonify({"error": e.output.decode('utf-8')})
       try:
           run_output = subprocess.check_output([out_name], timeout=5)
           output = run_output.decode('utf-8')
           return jsonify({"output": output})
       except subprocess.TimeoutExpired:
           return jsonify({"error": "Execution timed out"})
       except Exception as e:
           return jsonify({"error": str(e)})
       finally:
           os.unlink(f_name)
           if os.path.exists(out_name):
               os.unlink(out_name)
   elif lang == "java":
       class_name = "Main"  # Assume main class is Main
       with tempfile.NamedTemporaryFile(suffix=".java", delete=False) as f:
           f.write(code.encode('utf-8'))
           f_name = f.name
       try:
           compile_output = subprocess.check_output(["javac", f_name], stderr=subprocess.STDOUT)
       except subprocess.CalledProcessError as e:
           os.unlink(f_name)
           return jsonify({"error": e.output.decode('utf-8')})
       try:
           run_output = subprocess.check_output(["java", "-cp", os.path.dirname(f_name), class_name], timeout=5)
           output = run_output.decode('utf-8')
           return jsonify({"output": output})
       except subprocess.TimeoutExpired:
           return jsonify({"error": "Execution timed out"})
       except Exception as e:
           return jsonify({"error": str(e)})
       finally:
           os.unlink(f_name)
           compiled_file = os.path.join(os.path.dirname(f_name), class_name + ".class")
           if os.path.exists(compiled_file):
               os.unlink(compiled_file)
   elif lang == "ruby":
       try:
           output = subprocess.check_output(["ruby", "-e", code], timeout=5).decode('utf-8')
           return jsonify({"output": output})
       except subprocess.TimeoutExpired:
           return jsonify({"error": "Execution timed out"})
       except Exception as e:
           return jsonify({"error": str(e)})
   elif lang == "rust":
       with tempfile.NamedTemporaryFile(suffix=".rs", delete=False) as f:
           f.write(code.encode('utf-8'))
           f_name = f.name
       out_name = f_name + ".out"
       try:
           compile_output = subprocess.check_output(["rustc", f_name, "-o", out_name], stderr=subprocess.STDOUT)
       except subprocess.CalledProcessError as e:
           os.unlink(f_name)
           return jsonify({"error": e.output.decode('utf-8')})
       try:
           run_output = subprocess.check_output([out_name], timeout=5)
           output = run_output.decode('utf-8')
           return jsonify({"output": output})
       except subprocess.TimeoutExpired:
           return jsonify({"error": "Execution timed out"})
       except Exception as e:
           return jsonify({"error": str(e)})
       finally:
           os.unlink(f_name)
           if os.path.exists(out_name):
               os.unlink(out_name)
   elif lang == "kotlin":
       with tempfile.NamedTemporaryFile(suffix=".kt", delete=False) as f:
           f.write(code.encode('utf-8'))
           f_name = f.name
       jar_name = f_name + ".jar"
       try:
           compile_output = subprocess.check_output(["kotlinc", f_name, "-include-runtime", "-d", jar_name], stderr=subprocess.STDOUT)
       except subprocess.CalledProcessError as e:
           os.unlink(f_name)
           return jsonify({"error": e.output.decode('utf-8')})
       try:
           run_output = subprocess.check_output(["java", "-jar", jar_name], timeout=5)
           output = run_output.decode('utf-8')
           return jsonify({"output": output})
       except subprocess.TimeoutExpired:
           return jsonify({"error": "Execution timed out"})
       except Exception as e:
           return jsonify({"error": str(e)})
       finally:
           os.unlink(f_name)
           if os.path.exists(jar_name):
               os.unlink(jar_name)
   elif lang == "typescript":
       with tempfile.NamedTemporaryFile(suffix=".ts", delete=False) as f:
           f.write(code.encode('utf-8'))
           f_name = f.name
       js_name = f_name.replace(".ts", ".js")
       try:
           compile_output = subprocess.check_output(["tsc", f_name], stderr=subprocess.STDOUT)
       except subprocess.CalledProcessError as e:
           os.unlink(f_name)
           return jsonify({"error": e.output.decode('utf-8')})
       try:
           run_output = subprocess.check_output(["node", js_name], timeout=5)
           output = run_output.decode('utf-8')
           return jsonify({"output": output})
       except subprocess.TimeoutExpired:
           return jsonify({"error": "Execution timed out"})
       except Exception as e:
           return jsonify({"error": str(e)})
       finally:
           os.unlink(f_name)
           if os.path.exists(js_name):
               os.unlink(js_name)
   else:
       return jsonify({"error": "Unsupported language"})

@app.route("/api/kitchen-predict", methods=["POST"])
def kitchen_predict():
   if "file" not in request.files: return jsonify({"error": "No file"})
   if kitchen_model is None: return jsonify({"label": "Model not loaded", "confidence": 0})
   try:
       file = request.files["file"]
       img_bytes = file.read()
       # Thủ công xử lý hình ảnh: Resize, normalize
       img = tf.keras.preprocessing.image.load_img(io.BytesIO(img_bytes), target_size=(224, 224))  # Giả sử input size 224x224
       img_array = tf.keras.preprocessing.image.img_to_array(img)
       img_array = np.expand_dims(img_array, axis=0)
       img_array /= 255.0  # Normalize thủ công

       # Dự đoán
       predictions = kitchen_model.predict(img_array)
       predicted_class = np.argmax(predictions[0])
       confidence = np.max(predictions[0]) * 100  # Confidence %

       label = kitchen_classes[predicted_class] if predicted_class < len(kitchen_classes) else "Unknown"

       return jsonify({"label": label, "confidence": confidence})
   except Exception as e:
       return jsonify({"label": f"Lỗi: {str(e)}", "confidence": 0})

@app.route("/api/delete_msg/<session_id>/<msg_id>", methods=["DELETE"])
def delete_msg(session_id, msg_id):
   if session_id in GLOBAL_SESSIONS:
       messages = GLOBAL_SESSIONS[session_id]["messages"]
       GLOBAL_SESSIONS[session_id]["messages"] = [m for m in messages if m.get("id") != msg_id]
       threading.Thread(target=save_sessions_background).start()
       return jsonify({"status": "deleted"})
   return jsonify({"error": "Session not found"})

if __name__ == "__main__":
   # CHẠY TRÊN CỔNG 5001
   print("🚀 ĐANG CHẠY TẠI: [http://127.0.0.1:5001](http://127.0.0.1:5001)")
   socketio.run(app, debug=True, port=5001, host='0.0.0.0', allow_unsafe_werkzeug=True, use_reloader=False)
