const fs = require('fs');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const QRCode = require('qrcode');
const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || process.env.WHATSAPP_SERVICE_PORT || 3001;
const SESSION_PATH = process.env.WHATSAPP_SESSION_PATH || './whatsapp-session';
const API_KEY = process.env.WHATSAPP_API_KEY || '';
const CHROME_PATH = process.env.CHROME_PATH || process.env.PUPPETEER_EXECUTABLE_PATH || '';

app.use(cors());
app.use(express.json());

let client;
let isReady = false;
let qrCode = null;
let lastError = null;
let connectedNumber = null;

fs.mkdirSync(SESSION_PATH, { recursive: true });

function requireKey(req, res, next) {
    if (!API_KEY) {
        return next();
    }
    const got = req.get('X-API-Key') || req.query.key || '';
    if (got !== API_KEY) {
        return res.status(401).json({ success: false, error: 'unauthorized' });
    }
    return next();
}

function formatPhone(phone) {
    let formatted = String(phone).replace(/\D/g, '');
    if (!formatted.startsWith('994') && formatted.length < 12) {
        formatted = '994' + formatted;
    }
    return formatted;
}

function initializeWhatsApp() {
    const puppeteer = {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
        ],
    };
    if (CHROME_PATH) {
        puppeteer.executablePath = CHROME_PATH;
    }

    client = new Client({
        authStrategy: new LocalAuth({ dataPath: SESSION_PATH }),
        puppeteer,
    });

    client.on('qr', (qr) => {
        console.log('QR CODE RECEIVED — scan with the restaurant WhatsApp (Linked Devices):');
        qrcode.generate(qr, { small: true });
        qrCode = qr;
        isReady = false;
        connectedNumber = null;
        lastError = null;
    });

    client.on('ready', async () => {
        isReady = true;
        qrCode = null;
        lastError = null;
        try {
            connectedNumber = client.info && client.info.wid
                ? client.info.wid.user
                : null;
        } catch (err) {
            connectedNumber = null;
        }
        console.log('WhatsApp client is ready.', connectedNumber || '');
    });

    client.on('authenticated', () => {
        console.log('WhatsApp authenticated.');
    });

    client.on('auth_failure', (msg) => {
        console.error('Authentication failed:', msg);
        isReady = false;
        lastError = String(msg);
    });

    client.on('disconnected', (reason) => {
        console.log('WhatsApp disconnected:', reason);
        isReady = false;
        connectedNumber = null;
        lastError = `disconnected: ${reason}`;
        setTimeout(() => {
            client.initialize().catch((err) => {
                lastError = err.message;
                console.error('Reconnect failed:', err);
            });
        }, 5000);
    });

    client.initialize().catch((err) => {
        lastError = err.message;
        console.error('WhatsApp initialize failed:', err);
    });
}

app.get('/health', (req, res) => {
    res.json({
        status: 'running',
        whatsapp_ready: isReady,
        timestamp: new Date().toISOString(),
    });
});

app.get('/status', requireKey, (req, res) => {
    res.json({
        ready: isReady,
        qr_available: Boolean(qrCode),
        connected_number: connectedNumber,
        last_error: lastError,
        message: isReady
            ? 'WhatsApp is connected and ready'
            : qrCode
                ? 'Please scan the QR code to authenticate'
                : lastError
                    ? 'WhatsApp failed to start'
                    : 'WhatsApp is initializing...',
    });
});

app.get('/qr.png', requireKey, async (req, res) => {
    if (isReady || !qrCode) {
        return res.status(404).json({
            success: false,
            message: isReady ? 'already authenticated' : 'qr not ready',
        });
    }
    try {
        const buffer = await QRCode.toBuffer(qrCode, { width: 320, margin: 2 });
        res.type('png').send(buffer);
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/send-message', requireKey, async (req, res) => {
    const { phone, message } = req.body || {};
    if (!phone || !message) {
        return res.status(400).json({
            success: false,
            error: 'Phone number and message are required',
        });
    }
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp is not ready. Please scan QR code first.',
            qr_available: Boolean(qrCode),
        });
    }
    try {
        const chatId = `${formatPhone(phone)}@c.us`;
        await client.sendMessage(chatId, message);
        console.log(`Message sent to ${phone}`);
        return res.json({ success: true, message: 'Message sent successfully', to: phone });
    } catch (error) {
        console.error('Error sending message:', error);
        return res.status(500).json({
            success: false,
            error: 'Failed to send message',
            details: error.message,
        });
    }
});

app.post('/notify-order-deletion', requireKey, async (req, res) => {
    const {
        owner_phone,
        admin_name,
        room_name,
        table_number,
        order_id,
        order_created_at,
        deleted_at,
        meal_name,
        quantity,
        price,
        reason_display,
        comment,
    } = req.body || {};

    if (!owner_phone) {
        return res.status(400).json({
            success: false,
            error: 'Owner phone number is required',
        });
    }
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp is not ready. Please scan QR code first.',
            qr_available: Boolean(qrCode),
        });
    }

    try {
        let message = '🚨 *SİFARİŞ MƏHSUL SİLİNDİ*\n\n';
        message += `👤 *Admin:* ${admin_name || 'N/A'}\n`;
        message += `🏠 *Zal:* ${room_name || 'N/A'}\n`;
        message += `🍽️ *Masa:* ${table_number || 'N/A'}\n`;
        message += `🆔 *Sifariş:* #${order_id || 'N/A'}\n\n`;
        message += `📦 *Məhsul:* ${meal_name || 'N/A'}\n`;
        message += `🔢 *Miqdar:* ${quantity || 0}\n`;
        message += `💰 *Qiymət:* ${price || 0} AZN\n\n`;
        message += `📋 *Səbəb:* ${reason_display || 'N/A'}\n\n`;
        message += `⏰ *Sifariş vaxtı:* ${order_created_at || 'N/A'}\n`;
        message += `🗑️ *Silinmə vaxtı:* ${deleted_at || 'N/A'}`;
        if (comment) {
            message += `\n\n💬 *Qeyd:* ${comment}`;
        }

        const chatId = `${formatPhone(owner_phone)}@c.us`;
        await client.sendMessage(chatId, message);
        console.log(`Order deletion notification sent to ${owner_phone}`);
        return res.json({
            success: true,
            message: 'Notification sent successfully',
            to: owner_phone,
        });
    } catch (error) {
        console.error('Error sending notification:', error);
        return res.status(500).json({
            success: false,
            error: 'Failed to send notification',
            details: error.message,
        });
    }
});

app.post('/logout', requireKey, async (req, res) => {
    try {
        if (client) {
            await client.logout();
        }
        isReady = false;
        connectedNumber = null;
        qrCode = null;
        return res.json({ success: true, message: 'Logged out successfully' });
    } catch (error) {
        console.error('Error logging out:', error);
        return res.status(500).json({
            success: false,
            error: 'Failed to logout',
            details: error.message,
        });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log('='.repeat(60));
    console.log(`WhatsApp service listening on 0.0.0.0:${PORT}`);
    console.log(`Session path: ${SESSION_PATH}`);
    console.log(`Chrome: ${CHROME_PATH || 'puppeteer default'}`);
    console.log('='.repeat(60));
    initializeWhatsApp();
});

process.on('SIGINT', async () => {
    if (client) {
        await client.destroy();
    }
    process.exit(0);
});
