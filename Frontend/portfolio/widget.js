(function() {
    const chatToggle = document.getElementById('chat-toggle');
    const chatWindow = document.getElementById('chat-window');
    const closeChat = document.getElementById('close-chat');
    const chatInput = document.getElementById('chat-input');
    const chatSend = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');

    // Toggle Chat Window
    chatToggle.addEventListener('click', () => {
        chatWindow.classList.toggle('hidden');
    });

    closeChat.addEventListener('click', () => {
        chatWindow.classList.add('hidden');
    });

    // Handle Sending Messages
    const sendMessage = async () => {
        const text = chatInput.value.trim();
        if (!text) return;

        // Add user message to UI
        const userMsgDiv = document.createElement('div');
        userMsgDiv.className = 'user-message';
        userMsgDiv.innerText = text;
        chatMessages.appendChild(userMsgDiv);
        chatInput.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Ensure this points to the correct backend API endpoint
        // If deployed to Render, it might be the Render URL
        // However, since the frontend is served by the backend directly, 
        // a relative path like '/api/chat' works perfectly for both local and production.
        const API_URL = '/api/chat'; 

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, session_id: 'demo-123' })
            });
            
            const data = await response.json();

            // Add AI response to UI
            const aiMsgDiv = document.createElement('div');
            aiMsgDiv.className = 'ai-message';
            aiMsgDiv.innerText = data.reply || "I am currently offline.";
            chatMessages.appendChild(aiMsgDiv);

        } catch (error) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'ai-message';
            errorDiv.innerText = "Connection error. Please try again later.";
            chatMessages.appendChild(errorDiv);
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    chatSend.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
})();
