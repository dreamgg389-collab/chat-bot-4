// Public Chat Logic - ศพฐ.4 Chatbot

let socket;
let sessionId = localStorage.getItem('spb4_session_id');
let chatStatus = 'bot'; // 'bot', 'admin', 'waiting'

// Generate UUID for session if not exists
if (!sessionId) {
    sessionId = 'session_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('spb4_session_id', sessionId);
}

document.addEventListener("DOMContentLoaded", () => {
    initChat();
    setupEventListeners();
});

function initChat() {
    // Connect to Socket.IO server
    socket = io();

    // Emitted when connection is established
    socket.on('connect', () => {
        console.log('Connected to server. Joining session:', sessionId);
        socket.emit('join_session', { session_id: sessionId });
    });

    // Handle session join confirmation and load history
    socket.on('session_joined', (data) => {
        // IP and User Agent elements removed from HTML
        chatStatus = data.status;
        updateStatusUI();

        // Load chat history
        const container = document.getElementById('chat-messages-container');
        container.innerHTML = ''; // Clear container

        if (data.history && data.history.length > 0) {
            data.history.forEach(msg => {
                appendMessage(msg.sender, msg.message_text, msg.timestamp, false);
            });
            scrollToBottom();
        } else {
            // Render default welcome message if empty history
            appendWelcomeMessage();
        }
    });

    // Handle incoming messages (either from bot or admin)
    socket.on('receive_message', (data) => {
        appendMessage(data.sender, data.message_text, data.timestamp);
    });

    // Handle status changes (takeover / release)
    socket.on('status_changed', (data) => {
        chatStatus = data.status;
        updateStatusUI();
        
        // Show status change announcement in chat
        if (data.status === 'admin') {
            appendSystemAnnouncement('👮 เจ้าหน้าที่ควบคุมการสนทนาอยู่ ณ ขณะนี้');
        } else if (data.status === 'bot') {
            appendSystemAnnouncement('🤖 ระบบบอทอัตโนมัติกลับมาทำงานควบคุมการตอบกลับ');
        } else if (data.status === 'waiting') {
            appendSystemAnnouncement('⏳ กำลังรอเจ้าหน้าที่เชื่อมต่อเข้าร่วมการสนทนา...');
        }
    });

    // Bot Typing indicators
    socket.on('bot_typing', () => {
        document.getElementById('typing-indicator').style.display = 'flex';
        scrollToBottom();
    });

    socket.on('bot_stop_typing', () => {
        document.getElementById('typing-indicator').style.display = 'none';
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        appendSystemAnnouncement('❌ การเชื่อมต่อขาดหาย กำลังเชื่อมต่อใหม่...');
    });
}

function setupEventListeners() {
    // Quick Replies click handler
    const quickReplies = document.querySelectorAll('.quick-reply-btn');
    quickReplies.forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.getAttribute('data-text');
            submitMessage(text);
        });
    });

    // "Request Admin" special action
    const btnRequestAdmin = document.getElementById('btn-request-admin');
    if (btnRequestAdmin) {
        btnRequestAdmin.addEventListener('click', () => {
            socket.emit('request_admin', { session_id: sessionId });
        });
    }
}

function appendWelcomeMessage() {
    const welcomeText = `สวัสดีครับ ยินดีต้อนรับสู่ระบบบริการข้อมูลอัตโนมัติ ศูนย์พิสูจน์หลักฐาน 4 (ศพฐ.4) 👮✨

ผมเป็นระบบแชทบอทอัจฉริยะ สามารถตอบคำถามและการใช้บริการด้านงานพิสูจน์หลักฐานต่าง ๆ ได้อย่างตรงไปตรงมา

ท่านสามารถพิมพ์คำถามที่ต้องการ หรือเลือกหัวข้อยอดนิยมด้านล่างเพื่อสืบค้นข้อมูลได้ทันทีครับ`;
    
    appendMessage('bot', welcomeText, new Date().toISOString(), false);
}

function appendSystemAnnouncement(text) {
    const container = document.getElementById('chat-messages-container');
    const announceDiv = document.createElement('div');
    announceDiv.className = 'animate-fade';
    announceDiv.style.cssText = 'align-self: center; margin: 10px 0; font-size: 0.8rem; background: rgba(255, 255, 255, 0.05); padding: 6px 16px; border-radius: 20px; border: 1px solid var(--border-light); color: var(--text-muted); text-align: center;';
    announceDiv.textContent = text;
    container.appendChild(announceDiv);
    scrollToBottom();
}

function updateStatusUI() {
    const dot = document.getElementById('system-status-dot');
    const text = document.getElementById('system-status-text');
    
    // Reset classes
    dot.className = 'status-dot';
    
    if (chatStatus === 'bot') {
        text.textContent = 'ระบบตอบรับอัตโนมัติ (Bot)';
    } else if (chatStatus === 'admin') {
        dot.classList.add('admin-mode');
        text.textContent = 'สนทนากับเจ้าหน้าที่ (Live)';
    } else if (chatStatus === 'waiting') {
        dot.classList.add('waiting-mode');
        text.textContent = 'กำลังรอการติดต่อเจ้าหน้าที่...';
    }
}

function appendMessage(sender, text, timestamp, animate = true) {
    const container = document.getElementById('chat-messages-container');
    
    const wrapper = document.createElement('div');
    wrapper.className = `msg-wrapper ${sender}`;
    if (!animate) {
        wrapper.classList.remove('animate-fade');
    }
    
    // Sender tag
    const senderDiv = document.createElement('div');
    senderDiv.className = 'msg-sender';
    
    let senderLabel = 'คุณ';
    let badgeClass = '';
    
    if (sender === 'bot') {
        senderLabel = 'บอท ศพฐ.4';
        badgeClass = 'badge badge-bot';
    } else if (sender === 'admin') {
        senderLabel = 'เจ้าหน้าที่ ศพฐ.4';
        badgeClass = 'badge badge-admin';
    }
    
    if (badgeClass) {
        const badge = document.createElement('span');
        badge.className = badgeClass;
        badge.textContent = senderLabel;
        senderDiv.appendChild(badge);
    } else {
        senderDiv.textContent = senderLabel;
    }
    
    // Message Bubble
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    
    // Convert links to clickable anchors
    let formattedText = escapeHTML(text).replace(/\n/g, '<br>');
    bubble.innerHTML = formattedText;
    
    // Timestamp
    const timeDiv = document.createElement('div');
    timeDiv.className = 'msg-time';
    timeDiv.textContent = formatTime(timestamp);
    
    wrapper.appendChild(senderDiv);
    wrapper.appendChild(bubble);
    wrapper.appendChild(timeDiv);
    
    container.appendChild(wrapper);
    if (animate) {
        scrollToBottom();
    }
}

function sendUserMessage() {
    const input = document.getElementById('chat-input-field');
    const text = input.value.trim();
    if (!text) return;
    
    submitMessage(text);
    input.value = '';
}

function submitMessage(text) {
    // Append user message instantly
    const now = new Date().toISOString();
    appendMessage('user', text, now);
    
    // Send message to server via socket
    socket.emit('user_message', {
        session_id: sessionId,
        message_text: text
    });
}

function scrollToBottom() {
    const container = document.getElementById('chat-messages-container');
    container.scrollTop = container.scrollHeight;
}

function formatTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false });
    } catch (e) {
        return '';
    }
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}
