const API_URL = window.location.origin;
const sessionId = 'session_' + Date.now();
let isFirstMessage = true;

async function sendMessage() {
    const input = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const message = input.value.trim();
    
    if (!message) return;

    if (isFirstMessage) {
        document.querySelector('.welcome')?.remove();
        isFirstMessage = false;
    }

    input.disabled = true;
    sendBtn.disabled = true;
    input.value = '';

    addMessage(message, 'user');
    showTyping();

    try {
        const response = await fetch(`${API_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });

        const data = await response.json();
        hideTyping();

        if (data.success) {
            addMessage(data.response, 'bot', data.metadata?.tools_used || []);
        } else {
            addMessage('Sorry, something went wrong. Please try again.', 'bot', []);
        }
    } catch (error) {
        hideTyping();
        addMessage('Connection error. Please check your connection.', 'bot', []);
        console.error(error);
    }

    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
}

function sendQuick(text) {
    document.getElementById('message-input').value = text;
    sendMessage();
}

function addMessage(text, type, toolsUsed = []) {
    const container = document.getElementById('chat-container');
    const div = document.createElement('div');
    div.className = `message ${type}`;
    
    let html = text;
    const hasTable = /<table[^>]*>/i.test(text);
    
    if (hasTable) {
        html = html.replace(/\n/g, '');
    } else {
        const hasHtmlTags = /<(strong|br|ul|li|ol|div|span|em)[^>]*>/i.test(text);
        
        if (!hasHtmlTags) {
            html = html
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/\n/g, '<br>');
        }
    }
    
    let contentHtml = `<div class="content">${html}</div>`;
    
    if (type === 'bot' && toolsUsed && toolsUsed.length > 0) {
        const toolsId = 'tools_' + Date.now() + Math.random();
        contentHtml += `
            <div class="tools-used">
                <div class="tools-toggle" onclick="toggleTools('${toolsId}')">
                    <span class="tools-toggle-icon" id="${toolsId}_icon">▶</span>
                    <span>Tools used (${toolsUsed.length})</span>
                </div>
                <div class="tools-list" id="${toolsId}">
                    ${toolsUsed.map(tool => `
                        <div class="tool-item">
                            <span class="tool-icon"></span>
                            <span>${formatToolName(tool)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    div.innerHTML = contentHtml;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function toggleTools(id) {
    const toolsList = document.getElementById(id);
    const icon = document.getElementById(id + '_icon');
    
    if (toolsList.classList.contains('show')) {
        toolsList.classList.remove('show');
        icon.classList.remove('expanded');
    } else {
        toolsList.classList.add('show');
        icon.classList.add('expanded');
    }
}

function formatToolName(tool) {
    return tool
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function showTyping() {
    const container = document.getElementById('chat-container');
    const typing = document.createElement('div');
    typing.className = 'typing';
    typing.id = 'typing';
    typing.innerHTML = '<span></span><span></span><span></span>';
    container.appendChild(typing);
    container.scrollTop = container.scrollHeight;
}

function hideTyping() {
    document.getElementById('typing')?.remove();
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function checkStatus() {
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();
        document.getElementById('status-dot').style.background = 
            data.status === 'healthy' ? '#10b981' : '#ef4444';
    } catch {
        document.getElementById('status-dot').style.background = '#ef4444';
    }
}

checkStatus();
setInterval(checkStatus, 30000);
