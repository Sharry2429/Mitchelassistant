import { importKey, encryptMessage, decryptMessage } from './crypto.js';

let ws = null;
let cryptoKey = null;
let roomId = null;

// UI Elements
const overlay = document.getElementById('connection-overlay');
const mainUi = document.getElementById('main-ui');
const form = document.getElementById('connect-form');
const errorText = document.getElementById('connect-error');
const chatContainer = document.getElementById('chat-container');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const disconnectBtn = document.getElementById('disconnect-btn');

function appendMessage(text, type) {
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.textContent = text;
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorText.classList.add('hidden');
    
    const url = document.getElementById('relay-url').value;
    roomId = document.getElementById('room-id').value;
    const keyBase64 = document.getElementById('pairing-key').value;
    
    try {
        cryptoKey = await importKey(keyBase64);
    } catch (err) {
        errorText.textContent = "Invalid Pairing Key format.";
        errorText.classList.remove('hidden');
        return;
    }
    
    // Connect WS
    try {
        ws = new WebSocket(url);
    } catch (err) {
        errorText.textContent = "Invalid WebSocket URL.";
        errorText.classList.remove('hidden');
        return;
    }
    
    ws.onopen = () => {
        // Register as client
        ws.send(JSON.stringify({
            type: "register",
            role: "client",
            room: roomId
        }));
        
        overlay.classList.add('hidden');
        setTimeout(() => overlay.style.display = 'none', 300);
        mainUi.classList.remove('hidden');
        appendMessage("Connected to host.", "system");
    };
    
    ws.onmessage = async (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "message" && data.payload) {
                const decryptedStr = await decryptMessage(cryptoKey, data.payload);
                if (decryptedStr) {
                    const payloadData = JSON.parse(decryptedStr);
                    if (payloadData.reply) {
                        appendMessage(payloadData.reply, "bot");
                    }
                } else {
                    console.warn("Failed to decrypt message from host.");
                }
            }
        } catch (err) {
            console.error("Error parsing message", err);
        }
    };
    
    ws.onclose = () => {
        appendMessage("Disconnected from relay.", "system");
        setTimeout(disconnect, 2000);
    };
    
    ws.onerror = (err) => {
        errorText.textContent = "WebSocket connection failed.";
        errorText.classList.remove('hidden');
    };
});

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    
    chatInput.value = '';
    appendMessage(text, "user");
    
    // Encrypt and send
    const payload = JSON.stringify({ prompt: text });
    const encryptedBase64 = await encryptMessage(cryptoKey, payload);
    
    ws.send(JSON.stringify({
        type: "message",
        room: roomId,
        payload: encryptedBase64
    }));
});

function disconnect() {
    if (ws) ws.close();
    ws = null;
    cryptoKey = null;
    roomId = null;
    
    chatContainer.innerHTML = '<div class="message system">Connected securely via AES-GCM encryption. The relay server cannot read these messages.</div>';
    
    mainUi.classList.add('hidden');
    overlay.style.display = 'flex';
    setTimeout(() => overlay.classList.remove('hidden'), 50);
}

disconnectBtn.addEventListener('click', disconnect);
