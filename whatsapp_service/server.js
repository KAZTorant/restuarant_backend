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
const LEGACY_RESTAURANT = process.env.WHATSAPP_LEGACY_RESTAURANT === undefined
    ? 'qonaq-baku'
    : String(process.env.WHATSAPP_LEGACY_RESTAURANT || '').trim();

app.use(cors());
app.use(express.json());

const sessions = new Map();

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

function normalizeSlug(value) {
    const slug = String(value || '').trim().toLowerCase();
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 100) {
        return null;
    }
    return slug;
}

function blankState() {
    return {
        client: null,
        isReady: false,
        qrCode: null,
        lastError: null,
        connectedNumber: null,
        recovering: false,
        recoveryCount: 0,
        authenticating: false,
        manualLogout: false,
        starting: false,
        generation: 0,
        outbound: new Map(),
    };
}

function getState(slug) {
    if (!sessions.has(slug)) {
        sessions.set(slug, blankState());
    }
    return sessions.get(slug);
}

fs.mkdirSync(SESSION_PATH, { recursive: true });

function legacySessionDir() {
    return path.join(SESSION_PATH, 'session');
}

function namedSessionDir(slug) {
    return path.join(SESSION_PATH, `session-${slug}`);
}

function usesLegacyStore(slug) {
    if (slug !== LEGACY_RESTAURANT) {
        return false;
    }
    if (fs.existsSync(namedSessionDir(slug))) {
        return false;
    }
    return fs.existsSync(legacySessionDir());
}

function sessionDir(slug) {
    if (usesLegacyStore(slug)) {
        return legacySessionDir();
    }
    return namedSessionDir(slug);
}

function createAuth(slug) {
    if (usesLegacyStore(slug)) {
        return new LocalAuth({ dataPath: SESSION_PATH });
    }
    return new LocalAuth({ clientId: slug, dataPath: SESSION_PATH });
}

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

function savedSlugs() {
    let entries = [];
    try {
        entries = fs.readdirSync(SESSION_PATH, { withFileTypes: true });
    } catch (err) {
        return [];
    }
    const slugs = entries
        .filter((entry) => entry.isDirectory() && entry.name.startsWith('session-'))
        .map((entry) => entry.name.slice('session-'.length))
        .filter((slug) => normalizeSlug(slug) === slug);
    if (usesLegacyStore(LEGACY_RESTAURANT) && !slugs.includes(LEGACY_RESTAURANT)) {
        slugs.push(LEGACY_RESTAURANT);
    }
    return slugs;
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

function restaurantFrom(req) {
    return normalizeSlug((req.body && req.body.restaurant) || req.query.restaurant);
}

function formatPhone(phone) {
    let formatted = String(phone).replace(/\D/g, '');
    if (!formatted.startsWith('994') && formatted.length < 12) {
        formatted = '994' + formatted;
    }
    return formatted;
}

function phoneFromWid(wid) {
    const raw = String(wid || '').split('@')[0];
    const digits = raw.replace(/\D/g, '');
    return digits || null;
}

function shouldResetSession(err) {
    const message = err && err.message ? err.message : String(err || '');
    return /timed out|Execution context was destroyed|auth timeout|Target closed|Session closed|ProtocolError/i.test(message);
}

async function destroyClient(state) {
    if (!state.client) {
        return;
    }
    const current = state.client;
    state.client = null;
    try {
        await current.destroy();
    } catch (err) {
        console.error('Could not destroy WhatsApp client:', err.message);
    }
}

async function resetSession(slug, state) {
    await destroyClient(state);
    const dir = sessionDir(slug);
    clearStaleBrowserLocks(dir);
    if (usesLegacyStore(slug)) {
        logEvent('legacy_session_kept', { restaurant: slug });
        return;
    }
    fs.rmSync(dir, { recursive: true, force: true });
    logEvent('session_cleared', { restaurant: slug });
}

function scheduleRecovery(slug, state, err) {
    const message = err && err.message ? err.message : String(err || 'unknown error');
    state.lastError = message;
    state.isReady = false;
    state.authenticating = false;
    state.qrCode = null;
    state.connectedNumber = null;
    logEvent('recovery', { restaurant: slug, error: message, attempt: state.recoveryCount + 1 });
    if (state.recovering) {
        return;
    }
    if (state.recoveryCount >= 3) {
        console.error('Stopped WhatsApp recovery after repeated failures', slug);
        return;
    }
    state.recoveryCount += 1;
    state.recovering = true;
    setTimeout(async () => {
        try {
            if (shouldResetSession(err)) {
                await resetSession(slug, state);
            } else {
                await destroyClient(state);
                clearStaleBrowserLocks(sessionDir(slug));
            }
            state.recovering = false;
            state.starting = false;
            initializeWhatsApp(slug);
        } catch (recoveryErr) {
            state.recovering = false;
            state.starting = false;
            state.lastError = recoveryErr.message;
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

async function reportBackend(payload) {
    if (!BACKEND_URL) {
        return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
        const response = await fetch(`${BACKEND_URL}/api/users/whatsapp-delivery/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': API_KEY,
            },
            body: JSON.stringify(payload),
            signal: controller.signal,
        });
        if (!response.ok) {
            logEvent('delivery_report_failed', { status: response.status, restaurant: payload.restaurant });
        }
    } catch (err) {
        logEvent('delivery_report_error', { restaurant: payload.restaurant, error: err.message });
    } finally {
        clearTimeout(timer);
    }
}

async function sendIntake(text, source, sender, slug) {
    if (!BACKEND_URL) {
        throw new Error('BACKEND_URL is empty');
    }
    const response = await fetch(`${BACKEND_URL}/api/inventory/whatsapp-intake/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY,
        },
        body: JSON.stringify({ text, source, from: sender, restaurant: slug }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok && !payload.reply) {
        throw new Error(`intake ${response.status}`);
    }
    return payload.reply || 'Anbar yazılmadı.';
}

function rememberOutbound(state, waId, meta) {
    if (!waId) {
        return;
    }
    state.outbound.set(waId, meta);
}

async function handleIncoming(slug, state, msg) {
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
                logEvent('ocr_ok', { restaurant: slug, from, chars: recognized.length });
            }
        } catch (err) {
            logEvent('ocr_error', { restaurant: slug, from, error: err.message });
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

    logEvent('inbound', { restaurant: slug, from, source, chars: text.length });
    try {
        const reply = await sendIntake(text, source, from, slug);
        const replied = await msg.reply(reply);
        const waId = replied && replied.id ? replied.id._serialized : '';
        rememberOutbound(state, waId, { kind: 'intake_reply' });
        await reportBackend({
            event: 'message',
            restaurant: slug,
            wa_message_id: waId,
            ack: replied && typeof replied.ack === 'number' ? replied.ack : 1,
            recipient_phone: phoneFromWid(from),
            from_number: state.connectedNumber,
            body: reply,
            kind: 'intake_reply',
        });
        logEvent('inbound_replied', { restaurant: slug, from, source });
    } catch (err) {
        logEvent('inbound_error', { restaurant: slug, from, error: err.message });
        try {
            await msg.reply('Anbar yazılmadı. Bir az sonra yenidən göndərin.');
        } catch (replyErr) {
            logEvent('inbound_reply_error', { error: replyErr.message });
        }
    }
}

function initializeWhatsApp(slug) {
    const state = getState(slug);
    if (state.client || state.starting) {
        return state;
    }
    state.starting = true;

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

    let client;
    try {
        client = new Client({
            authStrategy: createAuth(slug),
            authTimeoutMs: 90000,
            puppeteer,
        });
    } catch (err) {
        state.starting = false;
        scheduleRecovery(slug, state, err);
        return state;
    }

    state.generation += 1;
    const generation = state.generation;
    state.manualLogout = false;
    state.client = client;
    state.starting = false;

    client.on('qr', (qr) => {
        logEvent('qr', { restaurant: slug, chars: qr.length });
        qrcode.generate(qr, { small: true });
        state.qrCode = qr;
        state.isReady = false;
        state.authenticating = false;
        state.connectedNumber = null;
        state.lastError = null;
        state.recoveryCount = 0;
        state.manualLogout = false;
    });

    client.on('ready', async () => {
        state.isReady = true;
        state.authenticating = false;
        state.qrCode = null;
        state.lastError = null;
        state.manualLogout = false;
        try {
            state.connectedNumber = client.info && client.info.wid
                ? client.info.wid.user
                : null;
        } catch (err) {
            state.connectedNumber = null;
        }
        logEvent('ready', {
            restaurant: slug,
            number: displayNumber(state.connectedNumber),
            digits: state.connectedNumber || null,
        });
        await reportBackend({
            event: 'session',
            restaurant: slug,
            from_number: state.connectedNumber,
            logout: false,
        });
    });

    client.on('loading_screen', (percent, message) => {
        logEvent('loading', { restaurant: slug, percent, message });
    });

    client.on('authenticated', () => {
        logEvent('authenticated', { restaurant: slug });
        state.authenticating = true;
        state.qrCode = null;
        state.lastError = null;
    });

    client.on('auth_failure', (msg) => {
        console.error('Authentication failed:', slug, msg);
        state.isReady = false;
        state.authenticating = false;
        state.lastError = String(msg);
    });

    client.on('message', (msg) => {
        handleIncoming(slug, state, msg).catch((err) => {
            logEvent('inbound_unhandled', { restaurant: slug, error: err.message });
        });
    });

    client.on('message_ack', (msg, ack) => {
        if (!msg || !msg.fromMe) {
            return;
        }
        const waId = msg.id && msg.id._serialized;
        const known = waId ? state.outbound.get(waId) : null;
        reportBackend({
            event: 'message',
            restaurant: slug,
            django_message_id: known && known.django_message_id,
            wa_message_id: waId || '',
            ack,
            recipient_phone: phoneFromWid(msg.to),
            from_number: state.connectedNumber,
            kind: (known && known.kind) || '',
            order_id: known && known.order_id,
        }).catch((err) => {
            logEvent('ack_report_error', { restaurant: slug, error: err.message });
        });
    });

    client.on('disconnected', (reason) => {
        if (state.generation !== generation) {
            logEvent('logout_disconnect_ignored', { restaurant: slug, reason });
            return;
        }
        logEvent('disconnected', { restaurant: slug, reason });
        state.isReady = false;
        state.authenticating = false;
        state.connectedNumber = null;
        if (state.manualLogout) {
            logEvent('logout_disconnect_ignored', { restaurant: slug });
            return;
        }
        state.lastError = `disconnected: ${reason}`;
        scheduleRecovery(slug, state, new Error(`disconnected: ${reason}`));
    });

    clearStaleBrowserLocks(sessionDir(slug));
    client.initialize().catch((err) => {
        console.error('WhatsApp initialize failed:', slug, err);
        scheduleRecovery(slug, state, err);
    });
    return state;
}

function ensureSession(slug, { start = false } = {}) {
    const state = getState(slug);
    const saved = fs.existsSync(sessionDir(slug));
    const canStart = (start || saved)
        && !state.client
        && !state.starting
        && !state.recovering
        && state.recoveryCount < 3;
    if (canStart) {
        initializeWhatsApp(slug);
    }
    return state;
}

function statusPayload(slug, state) {
    return {
        restaurant: slug,
        ready: state.isReady,
        authenticating: state.authenticating,
        qr_available: Boolean(state.qrCode),
        connected_number: state.connectedNumber,
        connected_number_display: displayNumber(state.connectedNumber),
        last_error: state.lastError,
        message: state.isReady
            ? 'WhatsApp is connected and ready'
            : state.qrCode
                ? 'Please scan the QR code to authenticate'
                : state.lastError
                    ? 'WhatsApp failed to start'
                    : 'WhatsApp is initializing...',
    };
}

async function sendOnSession(slug, phone, message, extra = {}) {
    const state = ensureSession(slug, { start: false });
    if (!state.isReady || !state.client) {
        logEvent('send_rejected', { restaurant: slug, to: phone, ready: state.isReady });
        return {
            ok: false,
            status: 503,
            body: {
                success: false,
                error: 'WhatsApp is not ready. Please scan QR code first.',
                qr_available: Boolean(state.qrCode),
                restaurant: slug,
            },
        };
    }
    const formatted = formatPhone(phone);
    const chatId = `${formatted}@c.us`;
    logEvent('send_start', { restaurant: slug, to: formatted, from: displayNumber(state.connectedNumber) });
    const sent = await state.client.sendMessage(chatId, message);
    const waId = sent && sent.id ? sent.id._serialized : '';
    const ack = sent && typeof sent.ack === 'number' ? sent.ack : 1;
    rememberOutbound(state, waId, {
        django_message_id: extra.django_message_id || null,
        kind: extra.kind || 'text',
        order_id: extra.order_id || null,
    });
    await reportBackend({
        event: 'message',
        restaurant: slug,
        django_message_id: extra.django_message_id || null,
        wa_message_id: waId,
        ack,
        recipient_phone: formatted,
        from_number: state.connectedNumber,
        body: message,
        kind: extra.kind || 'text',
        order_id: extra.order_id || null,
    });
    logEvent('send_ok', { restaurant: slug, to: formatted, wa_message_id: waId, ack });
    return {
        ok: true,
        status: 200,
        body: {
            success: true,
            message: 'Message sent successfully',
            to: formatted,
            restaurant: slug,
            wa_message_id: waId,
            ack,
            from_number: state.connectedNumber,
            body: message,
        },
    };
}

process.on('unhandledRejection', (reason) => {
    console.error('Unhandled rejection:', reason);
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught exception:', err);
});

app.get('/health', (req, res) => {
    const ready = [...sessions.values()].filter((state) => state.isReady).length;
    res.json({
        status: 'running',
        whatsapp_ready: ready > 0,
        sessions_ready: ready,
        timestamp: new Date().toISOString(),
    });
});

app.get('/status', requireKey, (req, res) => {
    const slug = restaurantFrom(req);
    if (!slug) {
        return res.status(400).json({ success: false, error: 'restaurant is required' });
    }
    const start = req.query.start === '1' || req.query.start === 'true';
    const state = ensureSession(slug, { start });
    return res.json(statusPayload(slug, state));
});

app.get('/qr.png', requireKey, async (req, res) => {
    const slug = restaurantFrom(req);
    if (!slug) {
        return res.status(400).json({ success: false, error: 'restaurant is required' });
    }
    const state = ensureSession(slug, { start: true });
    if (state.isReady || !state.qrCode) {
        return res.status(404).json({
            success: false,
            restaurant: slug,
            message: state.isReady ? 'already authenticated' : 'qr not ready',
        });
    }
    try {
        const buffer = await QRCode.toBuffer(state.qrCode, { width: 320, margin: 2 });
        res.type('png').send(buffer);
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/send-message', requireKey, async (req, res) => {
    const slug = restaurantFrom(req);
    const { phone, message, django_message_id, kind, order_id } = req.body || {};
    if (!slug) {
        return res.status(400).json({ success: false, error: 'restaurant is required' });
    }
    if (!phone || !message) {
        return res.status(400).json({
            success: false,
            error: 'Phone number and message are required',
        });
    }
    try {
        const result = await sendOnSession(slug, phone, message, {
            django_message_id,
            kind: kind || 'text',
            order_id,
        });
        return res.status(result.status).json(result.body);
    } catch (error) {
        console.error('Error sending message:', error);
        return res.status(500).json({
            success: false,
            error: 'Failed to send message',
            details: error.message,
            restaurant: slug,
        });
    }
});

app.post('/notify-order-deletion', requireKey, async (req, res) => {
    const slug = restaurantFrom(req);
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
        restaurant_name,
        django_message_id,
    } = req.body || {};

    if (!slug) {
        return res.status(400).json({ success: false, error: 'restaurant is required' });
    }
    if (!owner_phone) {
        return res.status(400).json({
            success: false,
            error: 'Owner phone number is required',
        });
    }

    let message = '🚨 *SİFARİŞ MƏHSUL SİLİNDİ*\n\n';
    message += `🏪 *Restoran:* ${restaurant_name || slug}\n`;
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

    try {
        const result = await sendOnSession(slug, owner_phone, message, {
            django_message_id,
            kind: 'order_deletion',
            order_id,
        });
        return res.status(result.status).json(result.body);
    } catch (error) {
        console.error('Error sending notification:', error);
        return res.status(500).json({
            success: false,
            error: 'Failed to send notification',
            details: error.message,
            restaurant: slug,
        });
    }
});

app.post('/logout', requireKey, async (req, res) => {
    const slug = restaurantFrom(req);
    if (!slug) {
        return res.status(400).json({ success: false, error: 'restaurant is required' });
    }
    const state = getState(slug);
    logEvent('logout_requested', { restaurant: slug, number: displayNumber(state.connectedNumber) });
    state.manualLogout = true;
    state.recoveryCount = 0;
    try {
        if (state.client) {
            await state.client.logout().catch((err) => {
                logEvent('logout_client_error', { restaurant: slug, error: err.message });
            });
            await destroyClient(state);
        }
        const dir = sessionDir(slug);
        clearStaleBrowserLocks(dir);
        fs.rmSync(dir, { recursive: true, force: true });
        state.isReady = false;
        state.authenticating = false;
        state.connectedNumber = null;
        state.qrCode = null;
        state.lastError = null;
        state.outbound.clear();
        logEvent('logout_ok', { restaurant: slug });
        await reportBackend({
            event: 'session',
            restaurant: slug,
            logout: true,
        });
        initializeWhatsApp(slug);
        return res.json({ success: true, message: 'Logged out successfully', restaurant: slug });
    } catch (error) {
        state.manualLogout = false;
        logEvent('logout_failed', { restaurant: slug, error: error.message });
        return res.status(500).json({
            success: false,
            error: 'Failed to logout',
            details: error.message,
            restaurant: slug,
        });
    }
});

function bootSessions() {
    const slugs = savedSlugs();
    logEvent('boot_sessions', { restaurants: slugs });
    slugs.forEach((slug) => ensureSession(slug, { start: true }));
}

app.listen(PORT, '0.0.0.0', () => {
    logEvent('listening', { port: PORT, session: SESSION_PATH, chrome: CHROME_PATH || 'default' });
    bootSessions();
});

process.on('SIGINT', async () => {
    for (const state of sessions.values()) {
        if (state.client) {
            await state.client.destroy();
        }
    }
    process.exit(0);
});
