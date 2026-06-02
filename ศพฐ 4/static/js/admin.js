// Admin Panel Logic - ศพฐ.4

let socket;
let currentTab = 'tab-live-chat';
let activeSessionId = null;
let savedPassword = localStorage.getItem('spb4_admin_password') || '';

document.addEventListener("DOMContentLoaded", () => {
    checkAuth();
    setupTabNavigation();
});

// --- Auth System ---

function checkAuth() {
    if (savedPassword) {
        verifyPassword(savedPassword).then(isValid => {
            if (isValid) {
                showDashboard();
            } else {
                showLogin();
            }
        });
    } else {
        showLogin();
    }
}

function showLogin() {
    document.getElementById('admin-login-screen').style.display = 'flex';
    document.getElementById('admin-dashboard-layout').style.display = 'none';
}

function showDashboard() {
    document.getElementById('admin-login-screen').style.display = 'none';
    document.getElementById('admin-dashboard-layout').style.display = 'flex';
    
    // Connect WebSocket as admin
    initAdminSocket();
    
    // Initial fetch for the active tab
    refreshActiveTabData();
}

async function verifyPassword(password) {
    try {
        const response = await fetch('/api/admin/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ passcode: password })
        });
        const data = await response.json();
        return data.success === true;
    } catch (e) {
        console.error('Verify error:', e);
        return false;
    }
}

function handleLoginSubmit() {
    const passwordInput = document.getElementById('admin-password-input');
    const password = passwordInput.value;
    const errorMsg = document.getElementById('login-error-msg');
    
    verifyPassword(password).then(isValid => {
        if (isValid) {
            savedPassword = password;
            localStorage.setItem('spb4_admin_password', password);
            errorMsg.style.display = 'none';
            passwordInput.value = '';
            showDashboard();
        } else {
            errorMsg.style.display = 'block';
            passwordInput.value = '';
            passwordInput.focus();
        }
    });
}

function handleLogout() {
    localStorage.removeItem('spb4_admin_password');
    savedPassword = '';
    activeSessionId = null;
    if (socket) {
        socket.disconnect();
    }
    showLogin();
}

// --- WebSocket Admin ---

function initAdminSocket() {
    if (socket) {
        socket.disconnect();
    }
    
    socket = io();
    
    socket.on('connect', () => {
        // Authenticate admin socket
        socket.emit('admin_join', { passcode: savedPassword });
    });
    
    socket.on('admin_authorized', (data) => {
        console.log('Admin socket authorized.');
        updateStatsUI(data.stats);
        renderSessionsList(data.sessions);
    });
    
    socket.on('admin_unauthorized', () => {
        alert('เซสชันผู้ดูแลระบบไม่ถูกต้อง กรุณาเข้าสู่ระบบใหม่');
        handleLogout();
    });
    
    socket.on('active_sessions_update', (sessions) => {
        renderSessionsList(sessions);
    });
    
    socket.on('stats_update', (stats) => {
        updateStatsUI(stats);
    });
    
    socket.on('new_chat_message', (data) => {
        // If message is for the currently selected session, render it
        if (activeSessionId === data.session_id) {
            appendConsoleMessage(data.sender, data.message_text, data.timestamp);
        }
    });
    
    socket.on('session_status_changed', (data) => {
        if (activeSessionId === data.session_id) {
            updateActiveSessionStatusUI(data.status);
        }
    });
}

// --- UI Stats & Tabs Navigation ---

function updateStatsUI(stats) {
    if (!stats) return;
    document.getElementById('stat-total-chats').textContent = stats.total_sessions || 0;
    document.getElementById('stat-waiting-chats').textContent = stats.status_counts ? stats.status_counts.waiting : 0;
    document.getElementById('stat-active-ips').textContent = stats.total_ips || 0;
    
    const waitBadge = document.getElementById('stat-waiting-chats');
    if (stats.status_counts && stats.status_counts.waiting > 0) {
        waitBadge.parentElement.style.borderColor = 'var(--status-waiting)';
        waitBadge.parentElement.style.background = 'rgba(245, 158, 11, 0.08)';
    } else {
        waitBadge.parentElement.style.borderColor = 'var(--border-light)';
        waitBadge.parentElement.style.background = 'rgba(255, 255, 255, 0.03)';
    }
}

function setupTabNavigation() {
    const buttons = document.querySelectorAll('.sidebar-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Hide all tabs
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            
            // Show target tab
            const targetId = btn.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');
            currentTab = targetId;
            
            refreshActiveTabData();
        });
    });
}

function refreshActiveTabData() {
    if (currentTab === 'tab-live-chat') {
        // Active sessions are updated via sockets automatically, but fetch once for safety
        fetchSessions();
    } else if (currentTab === 'tab-faq-manager') {
        fetchFAQs();
    } else if (currentTab === 'tab-ip-tracker') {
        fetchIPLogs();
    } else if (currentTab === 'tab-file-knowledge') {
        fetchDocuments();
    }
}

// --- Tab 1: Live Chat Console Logic ---

async function fetchSessions() {
    try {
        const response = await fetch('/api/admin/sessions', {
            headers: { 'Authorization': savedPassword }
        });
        if (response.status === 401) return handleLogout();
        const data = await response.json();
        renderSessionsList(data);
    } catch (e) {
        console.error('Fetch sessions error:', e);
    }
}

function renderSessionsList(sessions) {
    const container = document.getElementById('admin-sessions-container');
    container.innerHTML = '';
    
    if (!sessions || sessions.length === 0) {
        container.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-muted);">ไม่มีรายการสนทนา</div>';
        return;
    }
    
    sessions.forEach(session => {
        const item = document.createElement('div');
        item.className = `session-item animate-fade ${activeSessionId === session.id ? 'active' : ''}`;
        item.setAttribute('data-id', session.id);
        item.onclick = () => selectSession(session.id);
        
        let statusBadge = '';
        if (session.status === 'bot') {
            statusBadge = '<span class="badge badge-bot">🤖 Bot</span>';
        } else if (session.status === 'admin') {
            statusBadge = '<span class="badge badge-admin">🟢 Live</span>';
        } else if (session.status === 'waiting') {
            statusBadge = '<span class="badge badge-waiting">🟡 รอคิว</span>';
        }
        
        const lastMsg = session.last_message || 'ไม่มีข้อความ';
        const lastTime = formatShortTime(session.last_message_time || session.updated_at);
        
        item.innerHTML = `
            <div class="session-item-header">
                <span class="session-ip">${session.ip_address}</span>
                ${statusBadge}
            </div>
            <div class="session-preview">${escapeHTML(lastMsg)}</div>
            <div style="text-align: right; font-size: 0.65rem; color: var(--text-muted);">${lastTime}</div>
        `;
        container.appendChild(item);
    });
}

function filterSessions() {
    const query = document.getElementById('session-search-input').value.toLowerCase();
    const items = document.querySelectorAll('.session-item');
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(query)) {
            item.style.display = 'flex';
        } else {
            item.style.display = 'none';
        }
    });
}

async function selectSession(sessionId) {
    activeSessionId = sessionId;
    
    // Update active visual class
    document.querySelectorAll('.session-item').forEach(item => {
        if (item.getAttribute('data-id') === sessionId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // Toggle console view
    document.getElementById('admin-no-chat-selected').style.display = 'none';
    document.getElementById('admin-chat-console-active').style.display = 'flex';
    
    // Clear old messages and render loader
    const messagesContainer = document.getElementById('admin-console-messages-container');
    messagesContainer.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-muted);">กำลังโหลดประวัติการแชท...</div>';
    
    try {
        const response = await fetch(`/api/admin/sessions/${sessionId}`, {
            headers: { 'Authorization': savedPassword }
        });
        if (response.status === 401) return handleLogout();
        const data = await response.json();
        
        // Render Header details
        let ipDisplay = data.ip_address;
        if (data.location_info && data.location_info.status === 'success') {
            const city = data.location_info.city || '';
            const country = data.location_info.country || '';
            const isp = data.location_info.isp || '';
            ipDisplay = `${data.ip_address} 📍 ${city ? city + ', ' : ''}${country} (🏢 ${isp})`;
        } else if (data.location_info && data.location_info.status === 'local') {
            ipDisplay = `${data.ip_address} 🏠 (Local Network)`;
        }
        
        document.getElementById('active-session-ip').textContent = ipDisplay;
        document.getElementById('active-session-ua').textContent = data.user_agent;
        updateActiveSessionStatusUI(data.status);
        
        // Render history
        messagesContainer.innerHTML = '';
        if (data.history && data.history.length > 0) {
            data.history.forEach(msg => {
                appendConsoleMessage(msg.sender, msg.message_text, msg.timestamp, false);
            });
            scrollConsoleToBottom();
        } else {
            messagesContainer.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-muted);">ไม่มีข้อมูลประวัติการคุย</div>';
        }
        
        // Focus chat input
        document.getElementById('admin-message-input').focus();
    } catch (e) {
        console.error('Select session error:', e);
        messagesContainer.innerHTML = '<div style="text-align:center; padding:40px; color:var(--status-danger);">เกิดข้อผิดพลาดในการโหลดข้อมูล</div>';
    }
}

function updateActiveSessionStatusUI(status) {
    const badge = document.getElementById('active-session-status-badge');
    const toggleBtn = document.getElementById('btn-toggle-takeover');
    
    badge.className = 'badge';
    
    if (status === 'bot') {
        badge.classList.add('badge-bot');
        badge.textContent = '🤖 บอทอัตโนมัติ';
        toggleBtn.className = 'btn btn-primary';
        toggleBtn.textContent = '👮 เข้าตอบด้วยตนเอง (Takeover)';
    } else if (status === 'admin') {
        badge.classList.add('badge-admin');
        badge.textContent = '🟢 เจ้าหน้าที่ควบคุม';
        toggleBtn.className = 'btn btn-secondary';
        toggleBtn.textContent = '🤖 คืนให้บอทตอบ (Release)';
    } else if (status === 'waiting') {
        badge.classList.add('badge-waiting');
        badge.textContent = '🟡 รอเจ้าหน้าที่';
        toggleBtn.className = 'btn btn-primary animate-pulse';
        toggleBtn.textContent = '👮 เข้าตอบด้วยตนเอง (Takeover)';
    }
}

function toggleTakeover() {
    if (!activeSessionId) return;
    
    // Call server to swap state
    socket.emit('toggle_takeover', {
        session_id: activeSessionId,
        passcode: savedPassword
    });
}

function appendConsoleMessage(sender, text, timestamp, scroll = true) {
    const container = document.getElementById('admin-console-messages-container');
    
    const wrapper = document.createElement('div');
    wrapper.className = `msg-wrapper ${sender}`;
    
    const senderDiv = document.createElement('div');
    senderDiv.className = 'msg-sender';
    
    let senderLabel = 'ผู้ใช้';
    let badgeClass = '';
    
    if (sender === 'bot') {
        senderLabel = 'บอท ศพฐ.4';
        badgeClass = 'badge badge-bot';
    } else if (sender === 'admin') {
        senderLabel = 'เจ้าหน้าที่';
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
    
    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.innerHTML = escapeHTML(text).replace(/\n/g, '<br>');
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'msg-time';
    timeDiv.textContent = formatTime(timestamp);
    
    wrapper.appendChild(senderDiv);
    wrapper.appendChild(bubble);
    wrapper.appendChild(timeDiv);
    
    container.appendChild(wrapper);
    
    if (scroll) {
        scrollConsoleToBottom();
    }
}

function sendAdminMessage() {
    const input = document.getElementById('admin-message-input');
    const text = input.value.trim();
    if (!text || !activeSessionId) return;
    
    // Emit through socket
    socket.emit('admin_send_message', {
        session_id: activeSessionId,
        message_text: text,
        passcode: savedPassword
    });
    
    input.value = '';
    input.focus();
}

function scrollConsoleToBottom() {
    const container = document.getElementById('admin-console-messages-container');
    container.scrollTop = container.scrollHeight;
}

// --- Tab 2: FAQ Manager Logic ---

async function fetchFAQs() {
    try {
        const response = await fetch('/api/admin/faqs', {
            headers: { 'Authorization': savedPassword }
        });
        if (response.status === 401) return handleLogout();
        const data = await response.json();
        
        renderFAQsTable(data);
    } catch (e) {
        console.error('Fetch FAQ error:', e);
    }
}

function renderFAQsTable(faqs) {
    const tbody = document.getElementById('faq-table-body');
    const badge = document.getElementById('faq-total-badge');
    tbody.innerHTML = '';
    
    badge.textContent = `ทั้งหมด ${faqs.length} รายการ`;
    
    if (!faqs || faqs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">ไม่มีข้อมูล FAQ ในระบบคลังความรู้</td></tr>';
        return;
    }
    
    faqs.forEach(faq => {
        const tr = document.createElement('tr');
        
        // Format keywords as pills
        const keywordsPills = faq.keyword.split(',')
            .map(k => `<span class="faq-keyword-badge">${escapeHTML(k.trim())}</span>`)
            .join('');
            
        tr.innerHTML = `
            <td style="font-weight:600; color:var(--text-white);">${escapeHTML(faq.question)}</td>
            <td>${keywordsPills}</td>
            <td style="font-size:0.85rem; color:var(--text-muted); white-space:pre-wrap;">${escapeHTML(faq.answer)}</td>
            <td style="text-align:center;">
                <div class="action-btns" style="justify-content:center;">
                    <button class="btn btn-secondary btn-icon" onclick="editFAQ(${faq.id}, '${escapeJS(faq.question)}', '${escapeJS(faq.keyword)}', '${escapeJS(faq.answer)}')" title="แก้ไข">
                        <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                    </button>
                    <button class="btn btn-danger btn-icon" onclick="deleteFAQ(${faq.id})" title="ลบ">
                        <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function saveFAQ() {
    const id = document.getElementById('faq-id-field').value;
    const question = document.getElementById('faq-question').value.trim();
    const keyword = document.getElementById('faq-keywords').value.trim();
    const answer = document.getElementById('faq-answer').value.trim();
    
    if (!question || !keyword || !answer) return;
    
    const url = id ? `/api/admin/faqs/${id}` : '/api/admin/faqs';
    const method = id ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': savedPassword
            },
            body: JSON.stringify({ question, keyword, answer })
        });
        
        if (response.status === 401) return handleLogout();
        const res = await response.json();
        
        if (res.success) {
            resetFAQForm();
            fetchFAQs();
        } else {
            alert('ไม่สามารถบันทึกข้อมูลได้: ' + res.error);
        }
    } catch (e) {
        console.error('Save FAQ error:', e);
        alert('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์');
    }
}

function editFAQ(id, question, keyword, answer) {
    document.getElementById('faq-id-field').value = id;
    document.getElementById('faq-question').value = question;
    document.getElementById('faq-keywords').value = keyword;
    document.getElementById('faq-answer').value = answer;
    
    document.getElementById('faq-form-title').textContent = '📝 แก้ไขข้อมูลคำถาม-คำตอบคลังความรู้';
    document.getElementById('faq-submit-btn').textContent = 'บันทึกการแก้ไข';
    document.getElementById('faq-question').focus();
}

async function deleteFAQ(id) {
    if (!confirm('คุณแน่ใจว่าต้องการลบคำถามข้อนี้ออกจากบอทหรือไม่? การกระทำนี้ไม่สามารถย้อนคืนได้')) return;
    
    try {
        const response = await fetch(`/api/admin/faqs/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': savedPassword }
        });
        if (response.status === 401) return handleLogout();
        const res = await response.json();
        
        if (res.success) {
            fetchFAQs();
        } else {
            alert('ลบล้มเหลว: ' + res.error);
        }
    } catch (e) {
        console.error('Delete FAQ error:', e);
    }
}

function resetFAQForm() {
    document.getElementById('faq-id-field').value = '';
    document.getElementById('faq-form').reset();
    document.getElementById('faq-form-title').textContent = '➕ เพิ่มคำถาม-คำตอบคลังความรู้';
    document.getElementById('faq-submit-btn').textContent = 'บันทึกข้อมูล';
}

// --- Tab 3: IP Tracker Logic ---

async function fetchIPLogs() {
    try {
        const response = await fetch('/api/admin/ip-logs', {
            headers: { 'Authorization': savedPassword }
        });
        if (response.status === 401) return handleLogout();
        const data = await response.json();
        
        renderIPTrackerTable(data);
    } catch (e) {
        console.error('Fetch IP Logs error:', e);
    }
}

function renderIPTrackerTable(ipLogs) {
    const tbody = document.getElementById('ip-table-body');
    const badge = document.getElementById('ip-total-badge');
    tbody.innerHTML = '';
    
    badge.textContent = `คัดกรองทั้งหมด ${ipLogs.length} unique IPs`;
    
    if (!ipLogs || ipLogs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">ไม่มีข้อมูลบันทึก IP</td></tr>';
        return;
    }
    
    ipLogs.forEach(log => {
        const tr = document.createElement('tr');
        
        // Detect network type
        const ip = log.ip_address;
        let isInternal = false;
        if (ip === '127.0.0.1' || ip === '::1' || ip === 'localhost' ||
            ip.startsWith('10.') || ip.startsWith('192.168.') || 
            (ip.startsWith('172.') && parseInt(ip.split('.')[1]) >= 16 && parseInt(ip.split('.')[1]) <= 31)) {
            isInternal = true;
        }
        
        let networkInfo = '';
        if (log.location_info && log.location_info.status === 'success') {
            const city = escapeHTML(log.location_info.city || '');
            const country = escapeHTML(log.location_info.country || '');
            const isp = escapeHTML(log.location_info.isp || '');
            networkInfo = `
                <div style="font-size: 0.85rem; color: var(--text-primary); margin-bottom: 4px;">
                    <span title="Location">📍 ${city ? city + ', ' : ''}${country}</span>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted);" title="ISP">
                    🏢 ${isp}
                </div>
            `;
        } else if (log.location_info && log.location_info.status === 'local') {
            networkInfo = '<span class="badge badge-admin" style="background:rgba(52,211,153,0.1); border-color:var(--status-admin);">🏠 เครือข่ายภายใน (Local)</span>';
        } else {
            networkInfo = isInternal 
                ? '<span class="badge badge-admin" style="background:rgba(52,211,153,0.1); border-color:var(--status-admin);">🏠 เครือข่ายภายใน (Internal)</span>' 
                : '<span class="badge badge-bot" style="background:rgba(56,189,248,0.1); border-color:var(--status-bot);">🌐 เครือข่ายภายนอก (Internet)</span>';
        }
        // User agents render list
        let uaList = '';
        if (log.user_agents && log.user_agents.length > 0) {
            uaList = '<ul class="ua-list">';
            log.user_agents.forEach(ua => {
                uaList += `<li title="${escapeHTML(ua)}">${escapeHTML(ua)}</li>`;
            });
            uaList += '</ul>';
        } else {
            uaList = '-';
        }
        
        tr.innerHTML = `
            <td style="font-weight:700; color:var(--text-white); font-family:var(--font-eng); font-size:1.05rem;">
                <span style="cursor:pointer; text-decoration:underline;" onclick="findSessionForIP('${ip}')" title="กดเพื่อหาเซสชันแชทและสนทนา">${ip}</span>
            </td>
            <td style="text-align:center; font-family:var(--font-eng); font-weight:700;">${log.access_count}</td>
            <td style="font-size:0.85rem; color:var(--text-muted);">${formatFullTime(log.last_access)}</td>
            <td>${networkInfo}</td>
            <td>${uaList}</td>
        `;
        tbody.appendChild(tr);
    });
}

function findSessionForIP(ip) {
    // Switch to tab live chat
    const liveChatBtn = document.querySelector('[data-target="tab-live-chat"]');
    if (liveChatBtn) {
        liveChatBtn.click();
    }
    
    // Find item in session list
    // Sockets will supply active sessions. Let's look through DOM
    const sessionItems = document.querySelectorAll('.session-item');
    let found = false;
    sessionItems.forEach(item => {
        const itemIp = item.querySelector('.session-ip').textContent.trim();
        if (itemIp === ip) {
            item.click();
            found = true;
        }
    });
    
    if (!found) {
        // Search in input filter
        const searchInput = document.getElementById('session-search-input');
        searchInput.value = ip;
        filterSessions();
        
        // Try again
        const visibleItems = document.querySelectorAll('.session-item[style*="display: flex"], .session-item:not([style*="display: none"])');
        if (visibleItems.length > 0) {
            visibleItems[0].click();
        } else {
            alert('ไม่พบเซสชันการแชทที่กำลังทำงานอยู่ของ IP: ' + ip + ' (ประวัติแชทอาจถูกลบไปแล้วหรือยังไม่มีการแชทเปิดอยู่)');
        }
    }
}

// --- General Utility Helpers ---

function formatTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    } catch (e) {
        return '';
    }
}

function formatShortTime(isoString) {
    try {
        const date = new Date(isoString);
        const now = new Date();
        if (date.toDateString() === now.toDateString()) {
            return date.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false });
        } else {
            return date.toLocaleDateString('th-TH', { month: 'short', day: 'numeric' }) + ' ' + date.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false });
        }
    } catch (e) {
        return '';
    }
}

function formatFullTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleDateString('th-TH', { year: 'numeric', month: 'long', day: 'numeric' }) + ' ' + date.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    } catch (e) {
        return '';
    }
}

function escapeHTML(str) {
    if (!str) return '';
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

function escapeJS(str) {
    if (!str) return '';
    return str.replace(/\\/g, '\\\\')
              .replace(/'/g, "\\'")
              .replace(/"/g, '\\"')
              .replace(/\n/g, '\\n')
              .replace(/\r/g, '\\r');
}

// --- Tab 4: File Knowledge Base Logic ---

async function fetchDocuments() {
    try {
        const response = await fetch('/api/admin/documents', {
            headers: { 'Authorization': savedPassword }
        });
        if (response.status === 401) return handleLogout();
        const data = await response.json();
        renderDocumentsTable(data);
    } catch (e) {
        console.error('Fetch documents error:', e);
    }
}

function renderDocumentsTable(docs) {
    const tbody = document.getElementById('doc-table-body');
    const badge = document.getElementById('doc-total-badge');
    tbody.innerHTML = '';
    
    badge.textContent = `ทั้งหมด ${docs.length} ไฟล์`;
    
    if (!docs || docs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">ไม่มีข้อมูลไฟล์ในระบบ</td></tr>';
        return;
    }
    
    docs.forEach(doc => {
        const tr = document.createElement('tr');
        
        let typeBadge = '';
        if (doc.file_type === 'pdf') {
            typeBadge = '<span class="badge" style="background:#e74c3c; color:white;">PDF</span>';
        } else if (doc.file_type === 'docx' || doc.file_type === 'doc') {
            typeBadge = '<span class="badge" style="background:#2980b9; color:white;">Word</span>';
        } else if (doc.file_type === 'csv') {
            typeBadge = '<span class="badge" style="background:#27ae60; color:white;">CSV</span>';
        } else {
            typeBadge = `<span class="badge" style="background:#7f8c8d; color:white;">${doc.file_type.toUpperCase()}</span>`;
        }
        
        tr.innerHTML = `
            <td style="font-weight:600; color:var(--text-white);">${escapeHTML(doc.filename)}</td>
            <td>${typeBadge}</td>
            <td style="font-size:0.85rem; color:var(--text-muted);">${formatFullTime(doc.created_at)}</td>
            <td style="font-size:0.85rem; color:var(--text-muted);">${escapeHTML(doc.content_preview)}...</td>
            <td style="text-align:center;">
                <div class="action-btns" style="justify-content:center;">
                    <button class="btn btn-secondary btn-icon" onclick="openDocEditModal(${doc.id}, '${escapeJS(doc.filename)}')" title="ดู/แก้ไขเนื้อหา">
                        <svg viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>
                    </button>
                    <button class="btn btn-danger btn-icon" onclick="deleteDocument(${doc.id})" title="ลบไฟล์">
                        <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function uploadDocument() {
    const fileInput = document.getElementById('doc-file');
    const file = fileInput.files[0];
    if (!file) return;
    
    const btn = document.getElementById('doc-upload-btn');
    btn.disabled = true;
    btn.textContent = 'กำลังอัพโหลดและอ่านไฟล์...';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/admin/documents', {
            method: 'POST',
            headers: { 'Authorization': savedPassword },
            body: formData
        });
        
        if (response.status === 401) return handleLogout();
        const res = await response.json();
        
        if (res.success) {
            fileInput.value = '';
            fetchDocuments();
        } else {
            alert('อัพโหลดล้มเหลว: ' + res.error);
        }
    } catch (e) {
        console.error('Upload error:', e);
        alert('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์');
    } finally {
        btn.disabled = false;
        btn.textContent = 'เริ่มอัพโหลดไฟล์';
    }
}

async function openDocEditModal(id, filename) {
    document.getElementById('doc-edit-id').value = id;
    document.getElementById('doc-edit-filename').textContent = 'ไฟล์: ' + filename;
    document.getElementById('doc-edit-content').value = 'กำลังโหลดเนื้อหา...';
    
    document.getElementById('doc-edit-modal').style.display = 'flex';
    
    try {
        const response = await fetch(`/api/admin/documents/${id}`, {
            headers: { 'Authorization': savedPassword }
        });
        if (response.status === 401) return handleLogout();
        const data = await response.json();
        
        document.getElementById('doc-edit-content').value = data.content;
    } catch (e) {
        console.error('Fetch document error:', e);
        document.getElementById('doc-edit-content').value = 'เกิดข้อผิดพลาดในการโหลดเนื้อหา';
    }
}

function closeDocEditModal() {
    document.getElementById('doc-edit-modal').style.display = 'none';
}

async function saveDocumentEdit() {
    const id = document.getElementById('doc-edit-id').value;
    const content = document.getElementById('doc-edit-content').value;
    
    const btn = document.getElementById('doc-save-btn');
    btn.disabled = true;
    btn.textContent = 'กำลังบันทึก...';
    
    try {
        const response = await fetch(`/api/admin/documents/${id}`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': savedPassword
            },
            body: JSON.stringify({ content })
        });
        
        if (response.status === 401) return handleLogout();
        const res = await response.json();
        
        if (res.success) {
            closeDocEditModal();
            fetchDocuments();
        } else {
            alert('บันทึกล้มเหลว: ' + res.error);
        }
    } catch (e) {
        console.error('Save doc error:', e);
        alert('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์');
    } finally {
        btn.disabled = false;
        btn.textContent = 'บันทึกเนื้อหา';
    }
}

async function deleteDocument(id) {
    if (!confirm('คุณแน่ใจว่าต้องการลบไฟล์นี้ออกจากระบบ? เนื้อหาที่ AI เรียนรู้จากไฟล์นี้จะหายไปด้วย')) return;
    
    try {
        const response = await fetch(`/api/admin/documents/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': savedPassword }
        });
        if (response.status === 401) return handleLogout();
        const res = await response.json();
        
        if (res.success) {
            fetchDocuments();
        } else {
            alert('ลบล้มเหลว: ' + res.error);
        }
    } catch (e) {
        console.error('Delete doc error:', e);
    }
}

