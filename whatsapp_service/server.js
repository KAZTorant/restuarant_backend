const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { execFile } = require('child_process');
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
const BACKEND_URL = (process.env.BACKEND_URL || '').replace(/\/$/, '');

app.use(cors());
app.use(express.json());

let client;
let isReady = false;
let qrCode = null;
let lastError = null;
let connectedNumber = null;
let recovering = false;
let recoveryCount = 0;
let authenticating = false;
let manualLogout = false;

function logEvent(event, details) {
    const extra = details ? ` ${JSON.stringify(details)}` : '';
    console.log(`WA ${event}${extra}`);
}

function displayNumber(raw) {
    const digits = String(raw || '').replace(/\D/g, '');
    if (!digits) {
        return null;
    }
    if (digits.startsWith('994') && digits.length === 12) {
        return `+${digits.slice(0, 3)} ${digits.slice(3, 5)} ${digits.slice(5, 8)} ${digits.slice(8, 10)} ${digits.slice(10)}`;
    }
    return `+${digits}`;
}

fs.mkdirSync(SESSION_PATH, { recursive: true });

function clearStaleBrowserLocks(dir) {
    const lockNames = new Set([
        'SingletonLock',
        'SingletonCookie',
        'SingletonSocket',
        'DevToolsActivePort',
    ]);
    const stack = [dir];
    while (stack.length) {
        const current = stack.pop();
        let entries = [];
        try {
            entries = fs.readdirSync(current, { withFileTypes: true });
        } catch (err) {
            continue;
        }
        for (const entry of entries) {
            const full = path.join(current, entry.name);
            if (entry.isDirectory()) {
                stack.push(full);
            } else if (lockNames.has(entry.name)) {
                try {
                    fs.rmSync(full, { force: true });
                    console.log('Removed stale browser lock:', full);
                } catch (err) {
                    console.error('Could not remove lock', full, err.message);
                }
            }
        }
    }
}

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

function sessionDir() {
    return path.join(SESSION_PATH, 'session');
}

function shouldResetSession(err) {
    const message = err && err.message ? err.message : String(err || '');
    return /timed out|Execution context was destroyed|auth timeout|Target closed|Session closed|ProtocolError/i.test(message);
}

async function destroyClient() {
    if (!client) {
        return;
    }
    const current = client;
    client = null;
    try {
        await current.destroy();
    } catch (err) {
        console.error('Could not destroy WhatsApp client:', err.message);
    }
}

async function resetSession() {
    await destroyClient();
    clearStaleBrowserLocks(SESSION_PATH);
    fs.rmSync(sessionDir(), { recursive: true, force: true });
    logEvent('session_cleared');
}

function scheduleRecovery(err) {
    const message = err && err.message ? err.message : String(err || 'unknown error');
    lastError = message;
    isReady = false;
    authenticating = false;
    qrCode = null;
    connectedNumber = null;
    logEvent('recovery', { error: message, attempt: recoveryCount + 1 });
    if (recovering) {
        return;
    }
    if (recoveryCount >= 3) {
        console.error('Stopped WhatsApp recovery after repeated failures');
        return;
    }
    recoveryCount += 1;
    recovering = true;
    setTimeout(async () => {
        try {
            if (shouldResetSession(err)) {
                await resetSession();
            } else {
                await destroyClient();
                clearStaleBrowserLocks(SESSION_PATH);
            }
            recovering = false;
            initializeWhatsApp();
        } catch (recoveryErr) {
            recovering = false;
            lastError = recoveryErr.message;
            console.error('WhatsApp recovery failed:', recoveryErr);
        }
    }, 3000);
}

function runTesseract(file, lang) {
    return new Promise((resolve, reject) => {
        execFile(
            'tesseract',
            [file, 'stdout', '-l', lang, '--psm', '6'],
            { timeout: 25000, maxBuffer: 2 * 1024 * 1024 },
            (err, stdout) => {
                if (err) {
                    reject(err);
                    return;
                }
                resolve(stdout || '');
            },
        );
    });
}

async function readImageText(buffer) {
    const file = path.join(os.tmpdir(), `wa-${crypto.randomBytes(8).toString('hex')}.png`);
    fs.writeFileSync(file, buffer);
    try {
        try {
            return await runTesseract(file, 'aze+eng');
        } catch (err) {
            logEvent('ocr_lang_fallback', { error: err.message });
            return await runTesseract(file, 'eng');
        }
    } finally {
        fs.unlink(file, () => {});
    }
}

async function sendIntake(text, source, sender) {
    if (!BACKEND_URL) {
        throw new Error('BACKEND_URL is empty');
    }
    const response = await fetch(`${BACKEND_URL}/api/inventory/whatsapp-intake/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY,
        },
        body: JSON.stringify({ text, source, from: sender }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok && !payload.reply) {
        throw new Error(`intake ${response.status}`);
    }
    return payload.reply || 'Anbar yazılmadı.';
}

async function handleIncoming(msg) {
    if (!msg || msg.fromMe) {
        return;
    }
    const from = String(msg.from || '');
    if (from === 'status@broadcast' || from.endsWith('@g.us')) {
        return;
    }
    const skipTypes = new Set([
        'e2e_notification',
        'notification_template',
        'gp2',
        'protocol',
        'ciphertext',
        'revoked',
        'call_log',
    ]);
    if (skipTypes.has(msg.type)) {
        return;
    }

    let text = (msg.body || '').trim();
    let source = 'text';
    const isImage = msg.type === 'image' || (msg.hasMedia && String(msg.mimetype || '').startsWith('image/'));
    if (isImage || (msg.hasMedia && !text)) {
        try {
            const media = await msg.downloadMedia();
            if (media && String(media.mimetype || '').startsWith('image/') && media.data) {
                const recognized = (await readImageText(Buffer.from(media.data, 'base64'))).trim();
                source = 'ocr';
                text = [text, recognized].filter(Boolean).join('\n');
                logEvent('ocr_ok', { from, chars: recognized.length });
            }
        } catch (err) {
            logEvent('ocr_error', { from, error: err.message });
            try {
                await msg.reply('Şəkil oxunmadı. Mətni bu formatda göndərin:\nUn 10 kq');
            } catch (replyErr) {
                logEvent('inbound_reply_error', { error: replyErr.message });
            }
            return;
        }
    }

    if (!text) {
        if (source === 'ocr') {
            try {
                await msg.reply('Şəkildən mətn oxunmadı. Mətni bu formatda göndərin:\nUn 10 kq');
            } catch (replyErr) {
                logEvent('inbound_reply_error', { error: replyErr.message });
            }
        }
        return;
    }

    logEvent('inbound', { from, source, chars: text.length });
    try {
        const reply = await sendIntake(text, source, from);
        await msg.reply(reply);
        logEvent('inbound_replied', { from, source });
    } catch (err) {
        logEvent('inbound_error', { from, error: err.message });
        try {
            await msg.reply('Anbar yazılmadı. Bir az sonra yenidən göndərin.');
        } catch (replyErr) {
            logEvent('inbound_reply_error', { error: replyErr.message });
        }
    }
}

function initializeWhatsApp() {
    const puppeteer = {
        headless: true,
        protocolTimeout: 90000,
        args: [
            '--headless=new',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
        ],
    };
    if (CHROME_PATH) {
        puppeteer.executablePath = CHROME_PATH;
    }

    client = new Client({
        authStrategy: new LocalAuth({ dataPath: SESSION_PATH }),
        authTimeoutMs: 90000,
        puppeteer,
    });

    client.on('qr', (qr) => {
        logEvent('qr', { chars: qr.length });
        qrcode.generate(qr, { small: true });
        qrCode = qr;
        isReady = false;
        authenticating = false;
        connectedNumber = null;
        lastError = null;
        recoveryCount = 0;
    });

    client.on('ready', async () => {
        isReady = true;
        authenticating = false;
        qrCode = null;
        lastError = null;
        try {
            connectedNumber = client.info && client.info.wid
                ? client.info.wid.user
                : null;
        } catch (err) {
            connectedNumber = null;
        }
        logEvent('ready', {
            number: displayNumber(connectedNumber),
            digits: connectedNumber || null,
        });
    });

    client.on('loading_screen', (percent, message) => {
        logEvent('loading', { percent, message });
    });

    client.on('authenticated', () => {
        logEvent('authenticated');
        authenticating = true;
        qrCode = null;
        lastError = null;
    });

    client.on('auth_failure', (msg) => {
        console.error('Authentication failed:', msg);
        isReady = false;
        authenticating = false;
        lastError = String(msg);
    });

    client.on('message', (msg) => {
        handleIncoming(msg).catch((err) => {
            logEvent('inbound_unhandled', { error: err.message });
        });
    });

    client.on('disconnected', (reason) => {
        logEvent('disconnected', { reason });
        isReady = false;
        authenticating = false;
        connectedNumber = null;
        if (manualLogout) {
            logEvent('logout_disconnect_ignored');
            return;
        }
        lastError = `disconnected: ${reason}`;
        scheduleRecovery(new Error(`disconnected: ${reason}`));
    });

    clearStaleBrowserLocks(SESSION_PATH);
    client.initialize().catch((err) => {
        console.error('WhatsApp initialize failed:', err);
        scheduleRecovery(err);
    });
}

process.on('unhandledRejection', (reason) => {
    console.error('Unhandled rejection:', reason);
    scheduleRecovery(reason instanceof Error ? reason : new Error(String(reason)));
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught exception:', err);
    scheduleRecovery(err);
});

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
        authenticating: authenticating,
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
        logEvent('send_rejected', { to: phone, ready: isReady, authenticating });
        return res.status(503).json({
            success: false,
            error: 'WhatsApp is not ready. Please scan QR code first.',
            qr_available: Boolean(qrCode),
        });
    }
    try {
        const chatId = `${formatPhone(phone)}@c.us`;
        logEvent('send_start', { to: formatPhone(phone) });
        await client.sendMessage(chatId, message);
        logEvent('send_ok', { to: formatPhone(phone) });
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
        logEvent('notify_rejected', {
            to: owner_phone,
            order_id,
            meal_name,
            ready: isReady,
            authenticating,
        });
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
        logEvent('notify_start', {
            to: formatPhone(owner_phone),
            from: displayNumber(connectedNumber),
            order_id,
            meal_name,
            table_number,
        });
        await client.sendMessage(chatId, message);
        logEvent('notify_ok', { to: formatPhone(owner_phone), order_id, meal_name });
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
    logEvent('logout_requested', { number: displayNumber(connectedNumber) });
    manualLogout = true;
    try {
        if (client) {
            await client.logout().catch((err) => {
                logEvent('logout_client_error', { error: err.message });
            });
            await destroyClient();
        }
        clearStaleBrowserLocks(SESSION_PATH);
        fs.rmSync(sessionDir(), { recursive: true, force: true });
        isReady = false;
        authenticating = false;
        connectedNumber = null;
        qrCode = null;
        lastError = null;
        logEvent('logout_ok');
        manualLogout = false;
        initializeWhatsApp();
        return res.json({ success: true, message: 'Logged out successfully' });
    } catch (error) {
        manualLogout = false;
        logEvent('logout_failed', { error: error.message });
        return res.status(500).json({
            success: false,
            error: 'Failed to logout',
            details: error.message,
        });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    logEvent('listening', { port: PORT, session: SESSION_PATH, chrome: CHROME_PATH || 'default' });
    initializeWhatsApp();
});

process.on('SIGINT', async () => {
    if (client) {
        await client.destroy();
    }
    process.exit(0);
});
