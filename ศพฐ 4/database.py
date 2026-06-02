import sqlite3
import os
import json
from datetime import datetime
from config import DATABASE_NAME

def get_db_connection():
    """Create a new database connection for the current thread/request."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db():
    """Initialize database tables and seed initial FAQ data if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Sessions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            ip_address TEXT,
            user_agent TEXT,
            status TEXT DEFAULT 'bot',  -- 'bot', 'admin' (takeover), 'waiting'
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE sessions ADD COLUMN user_name TEXT DEFAULT ''")
        cursor.execute("ALTER TABLE sessions ADD COLUMN user_email TEXT DEFAULT ''")
        cursor.execute("ALTER TABLE sessions ADD COLUMN location_info TEXT DEFAULT '{}'")
    except sqlite3.OperationalError:
        pass
    
    # 2. Messages Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            sender TEXT,                -- 'user', 'bot', 'admin'
            message_text TEXT,
            timestamp TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    ''')
    
    # 3. FAQ Table (Knowledge Base)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,               -- comma separated keywords for search
            question TEXT,              -- friendly title / question
            answer TEXT,                -- direct answer
            created_at TEXT
        )
    ''')
    
    # 4. IP Access Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_logs (
            ip_address TEXT PRIMARY KEY,
            access_count INTEGER DEFAULT 1,
            last_access TEXT,
            user_agents TEXT,           -- JSON array of user agents used
            location_info TEXT DEFAULT '{}'
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE ip_logs ADD COLUMN location_info TEXT DEFAULT '{}'")
    except sqlite3.OperationalError:
        pass
    
    # 5. Knowledge Files Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            file_path TEXT,
            file_type TEXT,
            content TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    
    # Check if FAQ is empty, seed initial data
    cursor.execute("SELECT COUNT(*) FROM faq")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        initial_faqs = [
            (
                "ติดต่อ,เบอร์โทร,สถานที่,ที่อยู่,ศพฐ.4,ศพฐ4,เบอร์ติดต่อ,ติดต่อยังไง",
                "ติดต่อ ศูนย์พิสูจน์หลักฐาน 4",
                "ศูนย์พิสูจน์หลักฐาน 4 (ศพฐ.4) ตั้งอยู่ที่ ถนนศูนย์ราชการ ตำบลในเมือง อำเภอเมืองขอนแก่น จังหวัดขอนแก่น 40000 \n📞 เบอร์โทรศัพท์: 043-241071 หรือ 043-246535 \n📧 อีเมล: forensic4@police.go.th \nเปิดทำการในวันและเวลาราชการ (จันทร์ - ศุกร์ 08:30 - 16:30 น.)"
            ),
            (
                "ลายนิ้วมือ,ตรวจประวัติ,ประวัติอาชญากร,เช็คประวัติ,ตรวจสอบประวัติ,พิมพ์มือ",
                "การขอตรวจสอบประวัติและลายนิ้วมือ",
                "การตรวจสอบประวัติบุคคลหรือพิมพ์ลายนิ้วมือ สามารถทำได้โดย:\n1. เข้าติดต่อด้วยตนเองที่ ศพฐ.4 หรือสถานีตำรวจ (โรงพัก) ใกล้บ้านท่าน\n2. เอกสารที่ต้องใช้: บัตรประจำตัวประชาชนตัวจริง พร้อมสำเนา 1 ชุด\n3. อัตราค่าธรรมเนียม: 100 บาทต่อราย (ยกเว้นกรณีมีหนังสือส่งตัวเป็นทางการจากหน่วยงานรัฐตามระเบียบ)\n4. ระยะเวลาดำเนินการ: ประมาณ 3-7 วันทำการ"
            ),
            (
                "เขม่าดินปืน,อาวุธปืน,กระสุน,ตรวจปืน,ยิงปืน",
                "การส่งพิสูจน์อาวุธปืนและเขม่าดินปืน",
                "การตรวจพิสูจน์เกี่ยวกับอาวุธปืนและคราบเขม่าดินปืน มีระเบียบปฏิบัติคือ:\n1. การส่งตรวจเก็บพยานหลักฐานเขม่าดินปืนในบุคคล ควรทำการเก็บตัวอย่างโดยเร็วที่สุด (แนะนำภายใน 6 ชั่วโมงหลังเกิดเหตุ)\n2. อุปกรณ์และอาวุธของกลางต้องนำส่งโดยพนักงานสอบสวนผู้รับผิดชอบคดีเท่านั้น โดยห้ามสัมผัสหรือทำลายรอยนิ้วมือหรือคราบ DNA บนตัวปืน\n3. เอกสารต้องมีหนังสือส่งตรวจพิสูจน์อย่างเป็นทางการลงนามโดยหัวหน้าพนักงานสอบสวน"
            ),
            (
                "ดีเอ็นเอ,ตรวจ dna,ตรวจดีเอ็นเอ,ตรวจพ่อแม่,ตรวจสายเลือด,พิสูจน์พ่อลูก",
                "การส่งตรวจพิสูจน์สารพันธุกรรม (DNA)",
                "การตรวจพิสูจน์ DNA แบ่งออกเป็น 2 กรณี:\n1. คดีความทางอาญา: พนักงานสอบสวนเป็นผู้ส่งบุคคลและวัตถุพยานมาตรวจพิสูจน์เพื่อประกอบสำนวนคดี\n2. กรณีบุคคลทั่วไป (ร้องขอตรวจพิสูจน์บิดา-มารดา-บุตร): ต้องติดต่อยื่นคำร้องอย่างเป็นทางการ ณ ศูนย์พิสูจน์หลักฐาน โดยบุคคลที่จะรับการตรวจ (พ่อ แม่ ลูก) จะต้องมาแสดงตัวพร้อมกัน นำบัตรประชาชนและสูติบัตรตัวจริงมาแสดง มีอัตราค่าธรรมเนียมประมาณ 5,000-6,000 บาทต่อคน"
            ),
            (
                "ที่เกิดเหตุ,ตรวจที่เกิดเหตุ,ไฟไหม้,เพลิงไหม้,ลักทรัพย์,ขโมยขึ้นบ้าน,งัดบ้าน,รถชน",
                "การตรวจสถานที่เกิดเหตุ (ครต.)",
                "เมื่อเกิดเหตุการณ์คดีอาญา (เช่น ลักทรัพย์ งัดบ้าน เพลิงไหม้ ฆาตกรรม):\n1. โปรดแจ้งพนักงานสอบสวนท้องที่ (ตำรวจ 191) ทันที\n2. พนักงานสอบสวนจะประสานงานแจ้ง ศพฐ.4 เข้าดำเนินการตรวจพิสูจน์\n3. **ข้อแนะนำสำคัญ:** กรุณาอย่าแตะต้อง ย้าย หรือทำความสะอาดสิ่งของในที่เกิดเหตุโดยเด็ดขาด เพื่อป้องกันไม่ให้ลายนิ้วมือแฝงหรือวัตถุพยานชีวภาพชำรุดเสียหาย"
            ),
            (
                "เอกสาร,ตรวจเอกสาร,ปลอมแปลง,เซ็นชื่อปลอม,ลายเซ็น,ปลอมลายมือ,เช็คปลอม",
                "การตรวจพิสูจน์เอกสารและเขียนปลอม",
                "งานตรวจพิสูจน์เอกสาร ศพฐ.4 ให้บริการตรวจสอบ:\n1. ตรวจสอบลายมือชื่อ เขียนปลอม หรือลายเซ็นลอกเลียนแบบบนเอกสารสัญญา เช็ค ใบมอบอำนาจ\n2. ตรวจสอบรอยแก้ไข ลบ ขูด ขีดฆ่า หรือสอดแทรกข้อความ\n3. การตรวจกระดาษ หมึก และลายพิมพ์นิ้วมือพิมพ์กดทับข้อความ\n*การตรวจต้องนำส่งโดยพนักงานสอบสวน หรือมีเอกสารต้นฉบับเปรียบเทียบที่เชื่อถือได้จำนวนพอสมควร"
            )
        ]
        
        cursor.executemany(
            "INSERT INTO faq (keyword, question, answer, created_at) VALUES (?, ?, ?, ?)",
            [(faq[0], faq[1], faq[2], now) for faq in initial_faqs]
        )
        conn.commit()
        
    conn.close()

# --- Sessions Helpers ---

def create_session(session_id, ip_address, user_agent, user_name='', user_email='', location_info='{}'):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    # Check if session exists
    cursor.execute("SELECT id, status FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    
    if row:
        # Update IP, UA and updated_at
        cursor.execute('''
            UPDATE sessions 
            SET ip_address = ?, user_agent = ?, user_name = ?, user_email = ?, location_info = ?, updated_at = ?
            WHERE id = ?
        ''', (ip_address, user_agent, user_name, user_email, location_info, now, session_id))
        status = row['status']
    else:
        # Create new session
        cursor.execute('''
            INSERT INTO sessions (id, ip_address, user_agent, user_name, user_email, location_info, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'bot', ?, ?)
        ''', (session_id, ip_address, user_agent, user_name, user_email, location_info, now, now))
        status = 'bot'
        
    conn.commit()
    conn.close()
    
    # Log the IP access
    log_ip_access(ip_address, user_agent, location_info)
    return status

def get_session(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_session_status(session_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE sessions 
        SET status = ?, updated_at = ?
        WHERE id = ?
    ''', (status, now, session_id))
    conn.commit()
    conn.close()

def get_active_sessions():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Get all sessions with their last message
    cursor.execute('''
        SELECT s.id, s.ip_address, s.user_agent, s.user_name, s.user_email, s.location_info, s.status, s.created_at, s.updated_at,
               (SELECT message_text FROM messages WHERE session_id = s.id ORDER BY timestamp DESC LIMIT 1) as last_message,
               (SELECT timestamp FROM messages WHERE session_id = s.id ORDER BY timestamp DESC LIMIT 1) as last_message_time
        FROM sessions s
        ORDER BY s.updated_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- Messages Helpers ---

def log_message(session_id, sender, message_text):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    # Insert message
    cursor.execute('''
        INSERT INTO messages (session_id, sender, message_text, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (session_id, sender, message_text, now))
    
    # Update session updated_at
    cursor.execute('''
        UPDATE sessions 
        SET updated_at = ?
        WHERE id = ?
    ''', (now, session_id))
    
    conn.commit()
    conn.close()

def get_messages(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT sender, message_text, timestamp 
        FROM messages 
        WHERE session_id = ? 
        ORDER BY timestamp ASC
    ''', (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- FAQ (Knowledge Base) Helpers ---

def find_faq_answer(message_text):
    """
    Search FAQ database by keywords. 
    It splits keywords in the database by comma and checks if any keyword appears in user message,
    or if user message matches the keyword. It returns the most specific answer.
    """
    if not message_text:
        return None
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM faq")
    faqs = cursor.fetchall()
    conn.close()
    
    msg_clean = message_text.lower().strip()
    
    best_match = None
    max_match_len = 0
    
    for faq in faqs:
        keywords = [k.strip().lower() for k in faq['keyword'].split(',')]
        for kw in keywords:
            # Match exact or match as substring in message
            if kw and (kw in msg_clean or msg_clean in kw):
                # We prioritize the longest keyword match as it's more specific
                if len(kw) > max_match_len:
                    max_match_len = len(kw)
                    best_match = faq['answer']
                    
    return best_match

def get_all_faq():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM faq ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_faq(keyword, question, answer):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO faq (keyword, question, answer, created_at)
        VALUES (?, ?, ?, ?)
    ''', (keyword, question, answer, now))
    conn.commit()
    conn.close()

def update_faq(faq_id, keyword, question, answer):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE faq 
        SET keyword = ?, question = ?, answer = ?
        WHERE id = ?
    ''', (keyword, question, answer, faq_id))
    conn.commit()
    conn.close()

def delete_faq(faq_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM faq WHERE id = ?", (faq_id,))
    conn.commit()
    conn.close()

# --- IP Access Logs Helpers ---

def log_ip_access(ip_address, user_agent, location_info="{}"):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute("SELECT access_count, user_agents FROM ip_logs WHERE ip_address = ?", (ip_address,))
    row = cursor.fetchone()
    
    if row:
        count = row['access_count'] + 1
        try:
            agents = json.loads(row['user_agents'])
        except Exception:
            agents = []
        if user_agent not in agents:
            agents.append(user_agent)
            
        cursor.execute('''
            UPDATE ip_logs 
            SET access_count = ?, last_access = ?, user_agents = ?, location_info = ?
            WHERE ip_address = ?
        ''', (count, now, json.dumps(agents), location_info, ip_address))
    else:
        agents = [user_agent]
        cursor.execute('''
            INSERT INTO ip_logs (ip_address, access_count, last_access, user_agents, location_info)
            VALUES (?, 1, ?, ?, ?)
        ''', (ip_address, now, json.dumps(agents), location_info))
        
    conn.commit()
    conn.close()

def get_ip_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ip_logs ORDER BY last_access DESC")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        item = dict(row)
        try:
            item['user_agents'] = json.loads(item['user_agents'])
        except Exception:
            item['user_agents'] = [item['user_agents']]
            
        try:
            if 'location_info' in item and item['location_info']:
                item['location_info'] = json.loads(item['location_info'])
            else:
                item['location_info'] = {}
        except Exception:
            item['location_info'] = {}
            
        result.append(item)
    return result

def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total sessions
    cursor.execute("SELECT COUNT(*) FROM sessions")
    total_sessions = cursor.fetchone()[0]
    
    # 2. Total messages
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]
    
    # 3. Total unique IPs
    cursor.execute("SELECT COUNT(*) FROM ip_logs")
    total_ips = cursor.fetchone()[0]
    
    # 4. Status distribution
    cursor.execute("SELECT status, COUNT(*) as cnt FROM sessions GROUP BY status")
    status_rows = cursor.fetchall()
    status_counts = {'bot': 0, 'admin': 0, 'waiting': 0}
    for row in status_rows:
        status_counts[row['status']] = row['cnt']
        
    conn.close()
    
    return {
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'total_ips': total_ips,
        'status_counts': status_counts
    }

# --- Knowledge Files Helpers ---

def add_knowledge_file(filename, file_path, file_type, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO knowledge_files (filename, file_path, file_type, content, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (filename, file_path, file_type, content, now))
    file_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return file_id

def get_all_knowledge_files():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, file_path, file_type, created_at, SUBSTR(content, 1, 100) as content_preview FROM knowledge_files ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_knowledge_file(file_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM knowledge_files WHERE id = ?", (file_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_knowledge_content():
    """Return all content from all files for AI context."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT filename, content FROM knowledge_files")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_knowledge_file_content(file_id, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE knowledge_files
        SET content = ?
        WHERE id = ?
    ''', (content, file_id))
    conn.commit()
    conn.close()

def delete_knowledge_file(file_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM knowledge_files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()

