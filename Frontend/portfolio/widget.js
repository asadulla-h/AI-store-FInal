(function() {
    if (document.getElementById('premium-ai-widget-container')) return;

    const style = document.createElement('style');
    style.innerHTML = `
        #premium-ai-widget-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            z-index: 2147483647;
        }
        #premium-ai-chat-button {
            width: 60px; height: 60px; border-radius: 50%;
            background: linear-gradient(135deg, #4A0E1C, #8B1E32);
            color: white; border: none; cursor: pointer;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            display: flex; align-items: center; justify-content: center;
            transition: transform 0.3s ease;
        }
        #premium-ai-chat-window {
            display: none; position: absolute; bottom: 80px; right: 0;
            width: 350px; height: 500px; background: #FAFAFA;
            border-radius: 12px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
            flex-direction: column; overflow: hidden; border: 1px solid #EAEAEA;
        }
        #premium-ai-chat-header {
            background: #2C2C2C; color: #F0F0F0; padding: 18px;
            font-size: 16px; font-weight: 500; text-align: center;
            border-bottom: 2px solid #8B1E32;
        }
        #premium-ai-chat-messages {
            flex: 1; padding: 15px; overflow-y: auto;
            display: flex; flex-direction: column; gap: 10px;
        }
        .ai-message {
            background: #EAEAEA; color: #333; padding: 10px 14px;
            border-radius: 12px 12px 12px 2px; align-self: flex-start; font-size: 14px;
        }
        .user-message {
            background: #8B1E32; color: white; padding: 10px 14px;
            border-radius: 12px 12px 2px 12px; align-self: flex-end; font-size: 14px;
        }
        #premium-ai-chat-input-container {
            display: flex; padding: 10px; background: white; border-top: 1px solid #EAEAEA;
        }
        #premium-ai-chat-input {
            flex: 1; padding: 12px; border: 1px solid #CCC; border-radius: 6px; outline: none;
        }
        #premium-ai-chat-send {
            background: #2C2C2C; color: white; border: none; padding: 0 15px;
            margin-left: 8px; border-radius: 6px; cursor: pointer; font-weight: bold;
        }
        #premium-ai-chat-send:disabled { opacity: 0.6; cursor: not-allowed; }
    `;
    document.head.appendChild(style);

    const container = document.createElement('div');
    container.id = 'premium-ai-widget-container';
    container.innerHTML = `
        <div id="premium-ai-chat-window">
            <div id="premium-ai-chat-header">Weave AI Concierge</div>
            <div id="premium-ai-chat-messages">
                <div class="ai-message">Welcome to Weave Wardrobe. How can I help you style your look today?</div>
            </div>
            <div id="premium-ai-chat-input-container">
                <input type="text" id="premium-ai-chat-input" placeholder="Ask about products..." autocomplete="off"/>
                <button id="premium-ai-chat-send">Send</button>
            </div>
        </div>
        <button id="premium-ai-chat-button" type="button" aria-label="Open chat">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
        </button>
    `;
    document.body.appendChild(container);

    const chatButton = document.getElementById('premium-ai-chat-button');
    const chatWindow = document.getElementById('premium-ai-chat-window');
    const chatInput = document.getElementById('premium-ai-chat-input');
    const chatSend = document.getElementById('premium-ai-chat-send');
    const chatMessages = document.getElementById('premium-ai-chat-messages');

    const API_URL = (typeof window !== 'undefined' && window.AI_WIDGET_API_URL)
        || (window.location.origin + '/api/chat');

    const SESSION_STORAGE_KEY = 'weave_ai_session_id';

    function getOrCreateSessionId() {
        try {
            let id = localStorage.getItem(SESSION_STORAGE_KEY);
            if (!id) {
                id = (typeof crypto !== 'undefined' && crypto.randomUUID)
                    ? crypto.randomUUID()
                    : 'sess-' + Date.now() + '-' + Math.random().toString(36).slice(2, 12);
                localStorage.setItem(SESSION_STORAGE_KEY, id);
            }
            return id;
        } catch (_) {
            return 'sess-' + Date.now() + '-' + Math.random().toString(36).slice(2, 12);
        }
    }

    const sessionId = getOrCreateSessionId();

    function parseReply(data) {
        if (!data || typeof data !== 'object') return null;
        if (typeof data.reply === 'string' && data.reply.trim()) return data.reply;
        if (typeof data.response === 'string' && data.response.trim()) return data.response;
        if (typeof data.message === 'string' && data.message.trim()) return data.message;
        if (typeof data.detail === 'string') return data.detail;
        if (Array.isArray(data.detail)) {
            return data.detail.map(function(d) { return d.msg || String(d); }).join(' ');
        }
        return null;
    }

    chatButton.onclick = () => {
        chatWindow.style.display = chatWindow.style.display === 'flex' ? 'none' : 'flex';
    };

    let inFlight = false;

    const sendMessage = async () => {
        const text = chatInput.value.trim();
        if (!text || inFlight) return;

        inFlight = true;
        chatSend.disabled = true;

        const userMsg = document.createElement('div');
        userMsg.className = 'user-message';
        userMsg.innerText = text;
        chatMessages.appendChild(userMsg);
        chatInput.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-Id': sessionId
                },
                body: JSON.stringify({ message: text, session_id: sessionId })
            });

            let data = {};
            try {
                data = await response.json();
            } catch (_) {
                data = {};
            }

            const aiMsg = document.createElement('div');
            aiMsg.className = 'ai-message';

            if (response.status === 429) {
                aiMsg.innerText = "You're sending messages too quickly. Please wait a moment.";
            } else if (!response.ok) {
                aiMsg.innerText = parseReply(data) || 'The concierge is temporarily unavailable. Please try again.';
            } else {
                aiMsg.innerText = parseReply(data) || 'Sorry, I could not generate a reply. Please try again.';
            }
            chatMessages.appendChild(aiMsg);
        } catch (e) {
            const err = document.createElement('div');
            err.className = 'ai-message';
            err.innerText = "Connection error. Check that the API is running and CORS allows this site.";
            chatMessages.appendChild(err);
        } finally {
            inFlight = false;
            chatSend.disabled = false;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    };

    chatSend.onclick = sendMessage;
    chatInput.onkeypress = (e) => { if (e.key === 'Enter') sendMessage(); };
})();
