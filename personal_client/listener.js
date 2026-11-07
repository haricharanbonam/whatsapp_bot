const { Client, LocalAuth, Buttons, Poll } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const http = require('http');

const HTTP_BRIDGE_PORT = 5001;

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-first-run',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        ]
    }
});

client.on('qr', (qr) => {
    console.log('\n--- SCAN THIS QR CODE WITH YOUR WHATSAPP ---');
    qrcode.generate(qr, { small: true });
});

let isClientReady = false;

client.on('ready', () => {
    isClientReady = true;
    console.log('\n Connected! WhatsApp Web Bridge is ready.');
    console.log(` Listening for :ai, /ai, /mern, /sql, and "join paid-burst" commands...\n`);
});

// Helper to sanitize chat IDs
function formatToChatId(to) {
    if (!to) return null;
    let clean = to.replace(/[^0-9]/g, '');
    if (!clean.endsWith('@c.us')) {
        clean = `${clean}@c.us`;
    }
    return clean;
}

// HTTP Server for FastAPI <-> WhatsApp Web Bridge
const server = http.createServer(async (req, res) => {
    res.setHeader('Content-Type', 'application/json');

    if (req.method === 'POST' && req.url === '/send-button') {
        let bodyStr = '';
        req.on('data', chunk => bodyStr += chunk);
        req.on('end', async () => {
            try {
                if (!isClientReady) {
                    res.writeHead(503);
                    return res.end(JSON.stringify({ error: 'WhatsApp client is not ready yet.' }));
                }

                const data = JSON.parse(bodyStr);
                const chatId = formatToChatId(data.to);
                const messageText = data.body || "Good morning!";
                const buttonText = data.buttonText || "join paid-burst";
                const title = data.title || "⚡ Paid-Burst Morning Sprint";
                const footer = data.footer || "Click below to join";

                let sentMsg = null;
                try {
                    // Try sending WhatsApp native Buttons
                    const buttonMsg = new Buttons(
                        messageText,
                        [{ id: 'join_paid_burst', body: buttonText }],
                        title,
                        footer
                    );
                    sentMsg = await client.sendMessage(chatId, buttonMsg);
                    console.log(`[Bridge] Interactive button sent to ${chatId}`);
                } catch (btnErr) {
                    console.log(`[Bridge] Native button fallback to Poll: ${btnErr.message}`);
                    // Fallback to native WhatsApp Poll (widely supported on all devices)
                    const pollMsg = new Poll(
                        `${title}\n\n${messageText}`,
                        [buttonText, "Snooze 30 mins"],
                        { allowMultipleAnswers: false }
                    );
                    sentMsg = await client.sendMessage(chatId, pollMsg);
                    console.log(`[Bridge] Interactive poll sent to ${chatId}`);
                }

                res.writeHead(200);
                res.end(JSON.stringify({ ok: true, id: sentMsg ? sentMsg.id._serialized : 'sent' }));
            } catch (err) {
                console.error('[Bridge] Error sending button message:', err.message);
                res.writeHead(500);
                res.end(JSON.stringify({ error: err.message }));
            }
        });
        return;
    }

    if (req.method === 'POST' && req.url === '/send-message') {
        let bodyStr = '';
        req.on('data', chunk => bodyStr += chunk);
        req.on('end', async () => {
            try {
                const data = JSON.parse(bodyStr);
                const chatId = formatToChatId(data.to);
                await client.sendMessage(chatId, data.body);
                res.writeHead(200);
                res.end(JSON.stringify({ ok: true }));
            } catch (err) {
                res.writeHead(500);
                res.end(JSON.stringify({ error: err.message }));
            }
        });
        return;
    }

    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(HTTP_BRIDGE_PORT, () => {
    console.log(`[Bridge Server] HTTP bridge listening on port ${HTTP_BRIDGE_PORT}`);
});

// Listen to incoming messages and personal messages
client.on('message_create', async (msg) => {
    const raw = (msg.body || '').trim();
    if (!raw) return;

    // Check triggers
    const isAiCommand = /^(\/ai|:ai)\b/i.test(raw);
    const isPaidBurst = /^(join\s+)?paid-burst$/i.test(raw);
    const isMernOrSql = /^(\/mern|\/sql|mern|sql)\b/i.test(raw);

    if (isAiCommand || isPaidBurst || isMernOrSql) {
        let prompt = raw;
        if (isAiCommand) {
            prompt = raw.replace(/^(\/ai|:ai)\s*/i, '');
        }

        console.log(`[Command Triggered] From: ${msg.from} | Query: "${prompt}"`);

        try {
            const res = await axios.post('http://127.0.0.1:8000/whatsapp/personal', {
                prompt: prompt,
                sender: msg.from
            });

            const replyText = res.data.reply || "[Bot]: Empty response received.";
            const chat = await msg.getChat();
            await chat.sendMessage(replyText);
            console.log("Reply sent successfully to chat!");
        } catch (err) {
            console.error("Failed to send reply. Reason:", err.response ? err.response.data : err.message);
        }
    }
});

client.initialize();
