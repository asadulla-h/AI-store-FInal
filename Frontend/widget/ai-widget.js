(function() {
    const style = document.createElement('style');
    style.innerHTML = `
        #premium-ai-widget-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            z-index: 999999;
        }
        #premium-ai-chat-button {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4A0E1C, #8B1E32);
            color: white;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.3s ease;
        }
        #premium-ai-chat-button:hover {
            transform: scale(1.05);
        }
        #premium-ai-chat-window {
            display: none;
            position: absolute;
            bottom: 80px;
            right: 0;
            width: 350px;
            height: 500px;
            background: #FAFAFA;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
            flex-direction: column;
            overflow: hidden;
            border: 1px solid #EAEAEA;
        }
        #premium-ai-chat-header {
            background: #2C2C2C;
            color: #F0F0F0;
            padding: 18px;
            font-size: 16px;
            font-weight: 500;
            letter-spacing: 0.5px;
            text-align: center;
            border-bottom: 2px solid #8B1E32;
        }
        #premium-ai-chat-messages {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .ai-message {
            background: #EAEAEA;
            color: #333;
            padding: 10px 14px;
            border-radius: 12px 12px 12px 2px;
            max-width: 80%;
            align-self: flex-start;
            font-size: 14px;
            line-height: 1.4;
        }
        .user-message {
            background: #8B1E32;
            color: white;
            padding: 10px 14px;
            border-radius: 12px 12px 2px 12px;
            max-width: 80%;
            align-self: flex-end;
            font-size: 14px;
            line-height: 1.4;
        }
        #premium-ai-chat-input-container {
            display: flex;
            padding: 10px;
            background: white;
            border-top: 1px solid #EAEAEA;
        }
        #premium-ai-chat-input {
            flex: 1;
            padding: 12px;
            border: 1px solid #CCC;
            border-radius: 6px;
            outline: none;
            font-size: 14px;
        }
        #premium-ai-chat-input:focus {
            border-color: #8B1E32;
        }
        #premium-ai-chat-send {
            background: #2C2C2C;
            color: white;
            border: none;
            padding: 0 15px;
            margin-left: 8px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
        }
        #premium-ai-chat-send:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
    `;
    document.head.appendChild(style);

    const container = document.createElement('div');
    container.id = 'premium-ai-widget-container';
    container.innerHTML = `
        <div id="premium-ai-chat-window">
            <div id="premium-ai-chat-header">Concierge Desk</div>
            <div id="premium-ai-chat-messages">
                <div class="ai-message">Welcome. How can I assist you in finding the perfect item today?</div>
            </div>
            <div id="premium-ai-chat-input-container">
                <input type="text" id="premium-ai-chat-input" placeholder="Type your message..." autocomplete="off"/>
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
        || 'http://127.0.0.1:8000/api/chat';

    const SESSION_STORAGE_KEY = 'premium_ai_session_id';

    function getOrCreateSessionId() {
        try {
            let id = localStorage.getItem(SESSION_STORAGE_KEY);
            if (!id) {
                id = (typeof crypto !== 'undefined' && crypto.randomUUID)
                    ? crypto.randomUUID()
                    : 'sess-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11);
                localStorage.setItem(SESSION_STORAGE_KEY, id);
            }
            return id;
        } catch (_) {
            return 'sess-' + Date.now() + '-' + Math.random().toString(36).slice(2, 11);
        }
    }

    const sessionId = getOrCreateSessionId();

    chatButton.addEventListener('click', () => {
        const open = chatWindow.style.display === 'flex';
        chatWindow.style.display = open ? 'none' : 'flex';
    });

    let inFlight = false;

    const sendMessage = async () => {
        const text = chatInput.value.trim();
        if (!text || inFlight) return;

        inFlight = true;
        chatSend.disabled = true;

        const userMsgDiv = document.createElement('div');
        userMsgDiv.className = 'user-message';
        userMsgDiv.innerText = text;
        chatMessages.appendChild(userMsgDiv);
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

            if (response.status === 429) {
                throw new Error('rate_limit');
            }

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'request_failed');
            }

            const aiMsgDiv = document.createElement('div');
            aiMsgDiv.className = 'ai-message';
            aiMsgDiv.innerText = data.reply || "I am currently offline.";
            chatMessages.appendChild(aiMsgDiv);

        } catch (error) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'ai-message';
            if (error.message === 'rate_limit') {
                errorDiv.innerText = "You're sending messages too quickly. Please wait a moment.";
            } else {
                errorDiv.innerText = "Connection error. Please try again later.";
            }
            chatMessages.appendChild(errorDiv);
        } finally {
            inFlight = false;
            chatSend.disabled = false;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    };

    chatSend.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
})();
