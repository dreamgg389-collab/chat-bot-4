import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from functools import wraps
from datetime import datetime
import json
import os
import requests
from werkzeug.utils import secure_filename

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:
    import docx
except ImportError:
    docx = None
try:
    import pandas as pd
except ImportError:
    pd = None

import config
import database

# Initialize App
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# Upload Folder config
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure Gemini API if available
has_gemini = False
try:
    from google import genai
    from google.genai import types as genai_types
    if config.GEMINI_API_KEY:
        gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
        has_gemini = True
        print("🤖 Gemini AI integration enabled.")
except ImportError:
    gemini_client = None
    print("⚠️ google-genai module not found. Run pip install google-genai")
except Exception as e:
    gemini_client = None
    print("⚠️ Failed to initialize Gemini API, running in offline mode:", e)

# Helper to get client IP
def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    elif request.headers.get("X-Real-IP"):
        ip = request.headers.get("X-Real-IP")
    else:
        ip = request.remote_addr
    return ip

def fetch_ip_info(ip):
    try:
        if ip == '127.0.0.1' or ip == '::1' or ip == 'localhost' or ip.startswith('192.168.') or ip.startswith('10.'):
            return json.dumps({"status": "local", "message": "Local Network"})
        response = requests.get(f"http://ip-api.com/json/{ip}?lang=th", timeout=3)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print("IP Fetch Error:", e)
    return '{}'

# Helper to simplify User Agent string
def get_simplified_ua(ua_string):
    if not ua_string:
        return "Unknown Device"
    ua = ua_string.lower()
    os_name = "Unknown OS"
    browser = "Unknown Browser"
    
    # Detect OS
    if "windows" in ua:
        os_name = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "android" in ua:
        os_name = "Android"
    elif "linux" in ua:
        os_name = "Linux"
        
    # Detect Browser
    if "chrome" in ua or "crios" in ua:
        browser = "Chrome"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "firefox" in ua or "fxios" in ua:
        browser = "Firefox"
    elif "edge" in ua or "edg" in ua:
        browser = "Edge"
    elif "opera" in ua or "opr" in ua:
        browser = "Opera"
        
    return f"{os_name} ({browser})"

# Auth Decorator for REST API
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        passcode = request.headers.get('Authorization') or (request.json.get('passcode') if request.is_json else None)
        if not passcode or passcode != config.ADMIN_PASSWORD:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

# Load scraped website context
website_context = ""
try:
    with open("scraped_website_data.json", "r", encoding="utf-8") as f:
        scraped_data = json.load(f)
        # Extract useful text from scraped data
        context_parts = []
        for page in scraped_data:
            if "title" in page and "content" in page:
                context_parts.append(f"--- หน้า: {page['title']} ---\n{page['content']}")
        website_context = "\n\n".join(context_parts)
except Exception as e:
    print("⚠️ Failed to load scraped website data:", e)

# Helper to call Gemini API
def get_gemini_response(history_list):
    if not has_gemini:
        return None
    try:
        # Load FAQ data dynamically
        faqs = database.get_all_faq()
        faq_text = "\n".join([f"คำถาม: {f['question']}\nคำตอบ: {f['answer']}" for f in faqs])
        
        # Add Knowledge files content
        knowledge_files = database.get_all_knowledge_content()
        knowledge_text = ""
        if knowledge_files:
            knowledge_parts = []
            for kf in knowledge_files:
                knowledge_parts.append(f"--- ข้อมูลจากไฟล์: {kf['filename']} ---\n{kf['content']}")
            knowledge_text = "\n\n".join(knowledge_parts)
            
        system_instruction = (
            "คุณคือแชทบอทบริการประชาชนอัจฉริยะ ของ ศูนย์พิสูจน์หลักฐาน 4 (ศพฐ.4) สำนักงานตำรวจแห่งชาติ "
            "โปรดตอบคำถามของผู้รับบริการชาวไทยอย่างสุภาพ เป็นมิตร และถูกต้องตรงประเด็น "
            "หากผู้ใช้ทักทาย ให้ทักทายกลับอย่างสุภาพ และสามารถพูดคุยโต้ตอบได้ทุกเรื่องอย่างเป็นธรรมชาติ\n\n"
            "ข้อมูลถาม-ตอบที่ควรรู้ (FAQ ของ ศพฐ.4):\n" + faq_text + "\n\n"
            "ข้อมูลเพิ่มเติมจากเว็บไซต์ของ ศพฐ.4:\n" + website_context + "\n\n"
            "ข้อมูลเพิ่มเติมจากไฟล์เอกสาร:\n" + knowledge_text
        )
        
        contents = []
        for msg in history_list[-20:]:  # Keep last 20 messages for context
            role = 'user' if msg['sender'] == 'user' else 'model'
            if not msg['message_text']: continue
            contents.append(genai_types.Content(
                role=role,
                parts=[genai_types.Part.from_text(text=msg['message_text'])]
            ))
            
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        return response.text
    except Exception as e:
        print("Gemini API Error:", e)
        return None

# --- HTTP Routing ---

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

# --- REST APIs ---

@app.route('/api/admin/verify', methods=['POST'])
def api_verify():
    data = request.json or {}
    passcode = data.get('passcode')
    if passcode == config.ADMIN_PASSWORD:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Incorrect password'}), 401

@app.route('/api/admin/sessions', methods=['GET'])
@require_auth
def api_sessions():
    sessions = database.get_active_sessions()
    return jsonify(sessions)

@app.route('/api/admin/sessions/<session_id>', methods=['GET'])
@require_auth
def api_session_detail(session_id):
    session = database.get_session(session_id)
    if not session:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
        
    try:
        if 'location_info' in session and session['location_info']:
            session['location_info'] = json.loads(session['location_info'])
        else:
            session['location_info'] = {}
    except Exception:
        session['location_info'] = {}
    
    history = database.get_messages(session_id)
    session['history'] = history
    return jsonify(session)

@app.route('/api/admin/faqs', methods=['GET'])
@require_auth
def api_faqs():
    faqs = database.get_all_faq()
    return jsonify(faqs)

@app.route('/api/admin/faqs', methods=['POST'])
@require_auth
def api_add_faq():
    data = request.json or {}
    question = data.get('question')
    keyword = data.get('keyword')
    answer = data.get('answer')
    
    if not question or not keyword or not answer:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400
        
    database.add_faq(keyword, question, answer)
    return jsonify({'success': True})

@app.route('/api/admin/faqs/<int:faq_id>', methods=['PUT'])
@require_auth
def api_update_faq(faq_id):
    data = request.json or {}
    question = data.get('question')
    keyword = data.get('keyword')
    answer = data.get('answer')
    
    if not question or not keyword or not answer:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400
        
    database.update_faq(faq_id, keyword, question, answer)
    return jsonify({'success': True})

@app.route('/api/admin/faqs/<int:faq_id>', methods=['DELETE'])
@require_auth
def api_delete_faq(faq_id):
    database.delete_faq(faq_id)
    return jsonify({'success': True})

@app.route('/api/admin/ip-logs', methods=['GET'])
@require_auth
def api_ip_logs():
    ip_logs = database.get_ip_logs()
    return jsonify(ip_logs)

# --- Document Knowledge APIs ---

def extract_text_from_file(file_path, filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    content = ""
    try:
        if ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif ext == 'pdf' and PyPDF2:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        content += text + "\n"
        elif ext in ['doc', 'docx'] and docx:
            doc = docx.Document(file_path)
            content = "\n".join([para.text for para in doc.paragraphs])
        elif ext == 'csv' and pd:
            df = pd.read_csv(file_path)
            content = df.to_string()
        else:
            # Fallback for unknown or unsupported binary files if missing libraries
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
    except Exception as e:
        print(f"Error extracting text from {filename}: {e}")
        content = f"Error extracting content: {str(e)}"
    return content

@app.route('/api/admin/documents', methods=['GET'])
@require_auth
def api_get_documents():
    docs = database.get_all_knowledge_files()
    return jsonify(docs)

@app.route('/api/admin/documents', methods=['POST'])
@require_auth
def api_upload_document():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
        
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
    content = extract_text_from_file(file_path, filename)
    
    file_id = database.add_knowledge_file(file.filename, file_path, ext, content)
    
    return jsonify({'success': True, 'file_id': file_id})

@app.route('/api/admin/documents/<int:file_id>', methods=['GET'])
@require_auth
def api_get_document(file_id):
    doc = database.get_knowledge_file(file_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify(doc)

@app.route('/api/admin/documents/<int:file_id>', methods=['PUT'])
@require_auth
def api_update_document(file_id):
    data = request.json or {}
    content = data.get('content')
    if content is None:
        return jsonify({'success': False, 'error': 'No content provided'}), 400
        
    database.update_knowledge_file_content(file_id, content)
    return jsonify({'success': True})

@app.route('/api/admin/documents/<int:file_id>', methods=['DELETE'])
@require_auth
def api_delete_document(file_id):
    doc = database.get_knowledge_file(file_id)
    if doc:
        try:
            if os.path.exists(doc['file_path']):
                os.remove(doc['file_path'])
        except Exception as e:
            print(f"Error removing file {doc['file_path']}: {e}")
            
    database.delete_knowledge_file(file_id)
    return jsonify({'success': True})

# --- Socket.IO Events ---

@socketio.on('join_session')
def handle_join_session(data):
    session_id = data.get('session_id')
    if not session_id:
        return
        
    # Get client IP and User Agent
    ip_address = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')
    user_agent_short = get_simplified_ua(user_agent)
    
    # Fetch detailed location info based on IP
    location_info = fetch_ip_info(ip_address)
    
    # Store/update in DB
    status = database.create_session(session_id, ip_address, user_agent, location_info=location_info)
    
    # Join socket room
    join_room(session_id)
    
    # Get chat history
    history = database.get_messages(session_id)
    
    # Confirm join and send data to client
    emit('session_joined', {
        'session_id': session_id,
        'ip_address': ip_address,
        'user_agent_short': user_agent_short,
        'status': status,
        'history': history
    })
    
    # Update admin panels
    broadcast_admin_updates()

@socketio.on('user_message')
def handle_user_message(data):
    session_id = data.get('session_id')
    message_text = data.get('message_text', '').strip()
    
    if not session_id or not message_text:
        return
        
    # Log message from user
    database.log_message(session_id, 'user', message_text)
    
    # Broadcast user message to other rooms/tabs of this user and to admins
    timestamp = datetime.now().isoformat()
    emit('receive_message', {
        'sender': 'user',
        'message_text': message_text,
        'timestamp': timestamp
    }, room=session_id, include_self=False)
    
    # Broadcast to admins
    socketio.emit('new_chat_message', {
        'session_id': session_id,
        'sender': 'user',
        'message_text': message_text,
        'timestamp': timestamp
    }, room='admin_room')
    
    # Retrieve current session status
    session = database.get_session(session_id)
    if not session:
        return
        
    status = session['status']
    
    if status == 'bot':
        # Simulate typing indicator
        emit('bot_typing', {}, room=session_id)
        socketio.sleep(1.0) # Dynamic thinking delay
        
        # Try Gemini AI first as primary responder
        answer = None
        if has_gemini:
            history = database.get_messages(session_id)
            answer = get_gemini_response(history)
            
        # If AI is offline or fails, fallback to exact FAQ match
        if not answer:
            answer = database.find_faq_answer(message_text)
            
        # Fallback if no matching FAQ and no Gemini
        if not answer:
            answer = (
                "ขออภัยครับ ระบบบอทไม่พบข้อมูลเฉพาะเจาะจงสำหรับประเด็นนี้ \n\n"
                "หากคุณต้องการตรวจสอบข้อมูลและรับการชี้แจงจากหน่วยงานโดยตรง โปรดกดเลือกปุ่ม "
                "'🙋 ต้องการคุยกับเจ้าหน้าที่' ทางด้านล่าง เพื่อขอคิวแชทติดต่อเจ้าหน้าที่ ศพฐ.4 ได้โดยตรงครับ"
            )
            
        # Log and send bot answer
        database.log_message(session_id, 'bot', answer)
        emit('bot_stop_typing', {}, room=session_id)
        
        bot_timestamp = datetime.now().isoformat()
        emit('receive_message', {
            'sender': 'bot',
            'message_text': answer,
            'timestamp': bot_timestamp
        }, room=session_id)
        
        # Notify admins of bot reply
        socketio.emit('new_chat_message', {
            'session_id': session_id,
            'sender': 'bot',
            'message_text': answer,
            'timestamp': bot_timestamp
        }, room='admin_room')
        
    elif status == 'waiting':
        # Prompt user to wait
        # (Could also optionally notify that the request is queued)
        pass
        
    # Update admin dashboard sessions list and statistics
    broadcast_admin_updates()

@socketio.on('request_admin')
def handle_request_admin(data):
    session_id = data.get('session_id')
    if not session_id:
        return
        
    # Update status to waiting
    database.update_session_status(session_id, 'waiting')
    
    # Emit status change to user
    emit('status_changed', {'status': 'waiting'}, room=session_id)
    
    # Broadcast status change to admins
    socketio.emit('session_status_changed', {
        'session_id': session_id,
        'status': 'waiting'
    }, room='admin_room')
    
    broadcast_admin_updates()

@socketio.on('admin_join')
def handle_admin_join(data):
    passcode = data.get('passcode')
    if passcode != config.ADMIN_PASSWORD:
        emit('admin_unauthorized', {})
        return
        
    join_room('admin_room')
    
    # Send current stats and sessions to newly joined admin
    stats = database.get_dashboard_stats()
    sessions = database.get_active_sessions()
    
    emit('admin_authorized', {
        'stats': stats,
        'sessions': sessions
    })

@socketio.on('toggle_takeover')
def handle_toggle_takeover(data):
    session_id = data.get('session_id')
    passcode = data.get('passcode')
    
    if passcode != config.ADMIN_PASSWORD or not session_id:
        return
        
    session = database.get_session(session_id)
    if not session:
        return
        
    # Swap status
    new_status = 'bot' if session['status'] in ('admin', 'waiting') else 'admin'
    database.update_session_status(session_id, new_status)
    
    # Notify user in room
    socketio.emit('status_changed', {'status': new_status}, room=session_id)
    
    # Notify admins
    socketio.emit('session_status_changed', {
        'session_id': session_id,
        'status': new_status
    }, room='admin_room')
    
    broadcast_admin_updates()

@socketio.on('admin_send_message')
def handle_admin_send_message(data):
    session_id = data.get('session_id')
    message_text = data.get('message_text', '').strip()
    passcode = data.get('passcode')
    
    if passcode != config.ADMIN_PASSWORD or not session_id or not message_text:
        return
        
    # Force takeover if admin sends message
    session = database.get_session(session_id)
    if session and session['status'] != 'admin':
        database.update_session_status(session_id, 'admin')
        socketio.emit('status_changed', {'status': 'admin'}, room=session_id)
        socketio.emit('session_status_changed', {
            'session_id': session_id,
            'status': 'admin'
        }, room='admin_room')
        
    # Log message
    database.log_message(session_id, 'admin', message_text)
    
    # Emit to user room
    timestamp = datetime.now().isoformat()
    socketio.emit('receive_message', {
        'sender': 'admin',
        'message_text': message_text,
        'timestamp': timestamp
    }, room=session_id)
    
    # Emit to other admins
    socketio.emit('new_chat_message', {
        'session_id': session_id,
        'sender': 'admin',
        'message_text': message_text,
        'timestamp': timestamp
    }, room='admin_room')
    
    broadcast_admin_updates()

def broadcast_admin_updates():
    """Helper to update all authenticated admins of sessions & stats changes."""
    stats = database.get_dashboard_stats()
    sessions = database.get_active_sessions()
    
    socketio.emit('stats_update', stats, room='admin_room')
    socketio.emit('active_sessions_update', sessions, room='admin_room')

# Main Start
if __name__ == '__main__':
    # Initialize DB on start
    database.init_db()
    
    print(f"🚀 Starting ศพฐ.4 Chatbot on http://localhost:{config.PORT}")
    socketio.run(app, host=config.HOST, port=config.PORT, debug=True, allow_unsafe_werkzeug=True)
