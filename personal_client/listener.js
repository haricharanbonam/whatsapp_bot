const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

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

client.on('ready', () => {
    console.log('\n Connected! Listening for :ai or /ai commands...\n');
});

// Listen to both incoming messages and your own sent messages
client.on('message_create', async (msg) => {
    const raw = (msg.body || '').trim();
    const isAiCommand = /^(\/ai|:ai)\b/i.test(raw);

    if (isAiCommand) {
        const prompt = raw.replace(/^(\/ai|:ai)\s*/i, '');
        console.log(`[Command Triggered] From: ${msg.from} | Query: "${prompt}"`);

        try {
            console.log("Calling FastAPI endpoint...");
            console.log("Prompt:", prompt);
            console.log("Sender:", msg.from);
            const res = await axios.post('http://127.0.0.1:8000/whatsapp/personal', {
                prompt: prompt,
                sender: msg.from
            });

            console.log("FastAPI Response:", res.data);
            const replyText = res.data.reply || "[Bot]: Empty response received.";

            // Try sending via chat instance first, fallback to client.sendMessage
            const chat = await msg.getChat();
            await chat.sendMessage(replyText);
            console.log("Reply sent successfully to chat!");

        } catch (err) {
            console.error("Failed to send reply. Reason:", err.response ? err.response.data : err.message);
        }
    }
});
client.initialize();