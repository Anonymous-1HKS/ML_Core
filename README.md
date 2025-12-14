SupML v30.0 - Visionary OS
SupML Screenshot
(Placeholder for SupML interface screenshot - Replace with actual image if available)
Introduction
SupML v30.0 is a web-based simulated operating system (OS) designed to demonstrate advanced AI, Machine Learning (ML), chat functionalities, code editing, and customizable user interfaces. It mimics a futuristic "Visionary OS" with a glassmorphism theme, integrating AI-powered chat, image recognition, multi-language code execution, and real-time data fetching (e.g., weather and news).
The project is divided into:

Frontend: A single-page application (SPA) built with HTML, CSS, and vanilla JavaScript, providing an interactive OS-like interface.
Backend: A Flask-based API server handling AI interactions, ML predictions, code execution, and data storage.

Key features include:

AI Chat with image upload support using Google Gemini.
ML-based object detection (general and kitchen-specific).
Multi-language code editor with live preview and execution.
Customizable settings for themes, colors, and effects.
Dashboard with real-time weather, news, and system stats.

This README provides a detailed explanation of the code structure, libraries, algorithms, and implementation for both frontend and backend.
System Requirements

Python: 3.12+ (for backend).
Node.js: Not required (frontend is vanilla JS).
Browsers: Modern browsers like Chrome, Firefox (for frontend features like WebRTC camera access).
Dependencies: Listed in backend (via pip) and frontend (CDN links).
Hardware: Webcam for ML scanning; sufficient RAM/CPU for ML models.
API Keys: Google API Key for Gemini AI (hardcoded in backend; replace with your own for production).

Installation
Backend Setup

Clone the repository:textgit clone <repository-url>
cd <repository-folder>
Install dependencies:textpip install flask flask-cors flask-socketio pillow numpy tensorflow google-generativeai subprocess tempfile
Note: Additional compilers/runtimes may be needed for code execution (e.g., gcc/g++ for C/C++, javac/java for Java, rustc for Rust, kotlinc for Kotlin, tsc/node for TypeScript, ruby for Ruby).

Update paths in app.py for ML models (e.g., Kitchen_utensils_model.h5 and Utensils.txt).
Run the server:textpython app.py
Server runs on http://127.0.0.1:5001.


Frontend Setup

No installation needed; open index.html via the backend server (served at root /).
For development, use a local server like Live Server in VS Code to avoid CORS issues.

Usage

Start the backend server.
Access the app at http://127.0.0.1:5001.
Login with dummy credentials (e.g., "admin"/"123") or skip if already logged in.
Navigate via the dock sidebar:
Dashboard: Weather, news, stats.
Chat: AI conversations with image support.
ML Scanner: General object detection.
Kitchen Scanner: Utensil-specific ML.
Code: Multi-language editor and runner.
Settings: Customize UI.

Lock screen to return to welcome page.

Code Structure and Explanation
Frontend (index.html)
The frontend is a single HTML file with embedded CSS and JavaScript, creating a responsive, OS-like interface. It uses no frameworks (vanilla JS) for simplicity and performance.
HTML Structure

Welcome/Login Screens: Overlay divs for initial loading and authentication.
App Container: Main layout with dock (sidebar) and main-view (content area).
Pages: Hidden divs toggled via JS (e.g., #page-dashboard, #page-chat).
Dashboard: Grid of widgets for weather, clock, news.
Chat: Sidebar for sessions, main window for messages, input with file upload.
ML/Kitchen: Video streams, capture buttons, result cards.
Code: Editor with line numbers, language selector, terminal output, preview pane.
Settings: Profile card and customizable options.


CSS (Embedded in <style>)

Theme Variables: CSS variables (--primary, --glass-blur) for dynamic theming (light/dark/auto).
Glassmorphism: Backdrop-filter for blur, gradients for fluid backgrounds.
Components: Buttons (.btn-liquid), messages (.msg, .bubble), widgets (.widget-card).
Animations: Keyframes for fluid BG flow, page zoom-in.
Custom Additions: Preview pane for code, trash icons for chat deletions.

JavaScript (Embedded in <script>)

Initialization: window.onload checks login state, initializes UI.
Navigation: nav(p) toggles pages and dock buttons.
ML Scanners:
startCamera() / startKitchenCamera(): Uses navigator.mediaDevices for webcam access.
captureAndPredict() / captureKitchenAndPredict(): Canvas capture, blob conversion, FormData POST to /api/predict or /api/kitchen-predict.
predictImage(): Handles uploads, displays results with confidence bars.
askAIAboutObject(): Transitions to chat with pre-filled query and image.

Chat System:
sendMessage(): Handles text/image FormData, POST to /api/chat, renders messages with Markdown (via marked.js).
loadSessions() / loadChat(id): Fetches and renders session history.
deleteMsg(sessionId, msgId, el): DELETE to /api/delete_msg/{sessionId}/{msgId}, removes UI element.
Socket.io for real-time (though minimal use in code).

Code Editor:
runCode(): POST to /api/execute with lang/code, handles HTML preview specially.
livePreview(): Real-time HTML rendering in preview pane.
updateLineNumbers(): Dynamic line numbering.
Terminal: Simulates commands like pip install.

Settings:
setBlur(), setColor(), toggleAnimations(), setTheme(): Dynamically update CSS variables/properties.

Utils:
fetchWeather(): Open-Meteo API for weather data.
fetchWorldNews(): RSS parsing from multiple sources (BBC, NYT, etc.) with DOMParser.
showToast(): Notification system.
Speech Recognition: For voice input in chat (Chrome-only).


Algorithms in Frontend:

Real-time Rendering: Uses marked.parse for Markdown in chat bubbles.
Image Handling: URL.createObjectURL for previews, canvas for captures.
Dynamic UI: Event listeners for inputs, fetches for async data.

Libraries (via CDN):

marked.min.js: Markdown parsing.
chart.js: Potential charting (not heavily used).
socket.io.min.js: Real-time messaging.
Font Awesome: Icons.

Backend (app.py)
The backend is a Flask app with SocketIO for real-time, handling API routes for chat, ML, code execution, and sessions. It uses threading for background saves.
Structure

Imports: os, io, json, uuid, contextlib, threading, subprocess, tempfile (for code exec), Flask/CORS/SocketIO, PIL, numpy, tensorflow, google.generativeai.
Config:
Gemini AI models: model_chat and model_code with API key.
ML Model: Loads TensorFlow Keras model for kitchen utensils.

Global State: GLOBAL_SESSIONS dict for chat sessions, persisted to JSON.
Routes:
/: Serves index.html.
/api/login: Dummy success.
/api/sessions: GET list, DELETE by ID.
/api/sessions/<id>: GET messages.
/api/delete_all: Clears sessions.
/api/chat: POST for Gemini chat with optional image; appends to session.
/api/predict: POST image to Gemini for general description.
/api/code: POST to generate code (unused in current frontend).
/api/execute: POST code/lang; executes via REPL or compilers:
Python: exec with stdout redirect.
C/C++: gcc/g++ compile/run via subprocess.
Java: javac/java.
Ruby: ruby -e.
Rust: rustc.
Kotlin: kotlinc/java.
TypeScript: tsc/node.
HTML: No execution (frontend handles preview).
Temp files for compilation, timeout=5s.

/api/kitchen-predict: POST image to loaded Keras model; preprocesses (resize/normalize), predicts class/confidence.
/api/delete_msg/<session_id>/<msg_id>: DELETE specific message from session.

Run: SocketIO on port 5001.

Algorithms in Backend:

Chat: Uses Gemini generate_content with text/image inputs.
ML Prediction (Kitchen): Image preprocessing (load_img, img_to_array, expand_dims, normalize), Keras predict for classification (softmax probabilities, argmax for class).
Code Execution: Secure temp file handling, subprocess with timeouts to prevent hangs/malicious code.
Session Management: UUID for IDs, threading for async JSON saves.

Libraries:

Flask Stack: Flask (web framework), CORS (cross-origin), SocketIO (real-time).
AI/ML: google-generativeai (Gemini), tensorflow/keras (model loading/prediction), PIL/numpy (image processing).
Utils: subprocess/tempfile (code exec), io/contextlib (stdout redirect), threading (background tasks).

Potential Improvements

Security: Sanitize code execution (e.g., sandboxing).
Scalability: Use a database instead of JSON for sessions.
Error Handling: More robust try/except in JS fetches.
Testing: Add unit tests for API routes and JS functions.

Contributing
Fork the repo, create a branch, submit PRs. Issues welcome.
License
MIT License - Free to use/modify with attribution.
(Generated on December 14, 2025)
