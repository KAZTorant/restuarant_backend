const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.WHATSAPP_SERVICE_PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// WhatsApp Client
let client;
let isReady = false;
let qrCode = null;

// Initialize WhatsApp Client
function initializeWhatsApp() {
    client = new Client({
        authStrategy: new LocalAuth({
            dataPath: './whatsapp-session'
        }),
        puppeteer: {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        }
    });

    // QR Code Event
    client.on('qr', (qr) => {
        console.log('📱 QR CODE RECEIVED - Scan this with your WhatsApp:');
        qrcode.generate(qr, { small: true });
        qrCode = qr;
        isReady = false;
    });

    // Ready Event
    client.on('ready', () => {
        console.log('✅ WhatsApp Client is ready!');
        isReady = true;
        qrCode = null;
    });

    // Authenticated Event
    client.on('authenticated', () => {
        console.log('✅ WhatsApp authenticated successfully');
    });

    // Authentication Failure Event
    client.on('auth_failure', (msg) => {
        console.error('❌ Authentication failed:', msg);
        isReady = false;
    });

    // Disconnected Event
    client.on('disconnected', (reason) => {
        console.log('⚠️ WhatsApp disconnected:', reason);
        isReady = false;
        console.log('🔄 Attempting to reconnect...');
        setTimeout(() => {
            client.initialize();
        }, 5000);
    });

    // Initialize the client
    client.initialize();
}

// API Routes

// Health Check
app.get('/health', (req, res) => {
    res.json({
        status: 'running',
        whatsapp_ready: isReady,
        timestamp: new Date().toISOString()
    });
});

// Get Status
app.get('/status', (req, res) => {
    res.json({
        ready: isReady,
        qr_code: qrCode,
        message: isReady 
            ? 'WhatsApp is connected and ready' 
            : qrCode 
                ? 'Please scan the QR code to authenticate' 
                : 'WhatsApp is initializing...'
    });
});

// Get QR Code
app.get('/qr', (req, res) => {
    if (isReady) {
        res.json({
            success: false,
            message: 'WhatsApp is already authenticated'
        });
    } else if (qrCode) {
        res.json({
            success: true,
            qr_code: qrCode
        });
    } else {
        res.json({
            success: false,
            message: 'QR code not available yet. Please wait...'
        });
    }
});

// Send Message
app.post('/send-message', async (req, res) => {
    const { phone, message } = req.body;

    // Validate request
    if (!phone || !message) {
        return res.status(400).json({
            success: false,
            error: 'Phone number and message are required'
        });
    }

    // Check if WhatsApp is ready
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp is not ready. Please scan QR code first.',
            qr_available: !!qrCode
        });
    }

    try {
        // Format phone number (remove spaces, dashes, etc.)
        let formattedPhone = phone.replace(/\D/g, '');
        
        // Add country code if not present
        if (!formattedPhone.startsWith('994') && formattedPhone.length < 12) {
            formattedPhone = '994' + formattedPhone;
        }

        // WhatsApp format: number@c.us
        const chatId = formattedPhone + '@c.us';

        // Send message
        await client.sendMessage(chatId, message);

        console.log(`✅ Message sent to ${phone}`);
        
        res.json({
            success: true,
            message: 'Message sent successfully',
            to: phone
        });
    } catch (error) {
        console.error('❌ Error sending message:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to send message',
            details: error.message
        });
    }
});

// Send Notification (specific for order deletion)
app.post('/notify-order-deletion', async (req, res) => {
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
        comment 
    } = req.body;

    // Validate request
    if (!owner_phone) {
        return res.status(400).json({
            success: false,
            error: 'Owner phone number is required'
        });
    }

    // Check if WhatsApp is ready
    if (!isReady) {
        return res.status(503).json({
            success: false,
            error: 'WhatsApp is not ready. Please scan QR code first.',
            qr_available: !!qrCode
        });
    }

    try {
        // Format message
        let message = `🚨 *SİFARİŞ MƏHSUL SİLİNDİ*\n\n`;
        message += `👤 *Admin:* ${admin_name || 'N/A'}\n`;
        message += `� *Zal:* ${room_name || 'N/A'}\n`;
        message += `�🍽️ *Masa:* ${table_number || 'N/A'}\n`;
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

        // Format phone number
        let formattedPhone = owner_phone.replace(/\D/g, '');
        if (!formattedPhone.startsWith('994') && formattedPhone.length < 12) {
            formattedPhone = '994' + formattedPhone;
        }

        const chatId = formattedPhone + '@c.us';

        // Send message
        await client.sendMessage(chatId, message);

        console.log(`✅ Order deletion notification sent to ${owner_phone}`);
        
        res.json({
            success: true,
            message: 'Notification sent successfully',
            to: owner_phone
        });
    } catch (error) {
        console.error('❌ Error sending notification:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to send notification',
            details: error.message
        });
    }
});

// Logout (clear session)
app.post('/logout', async (req, res) => {
    try {
        if (client) {
            await client.logout();
            console.log('📤 WhatsApp logged out');
        }
        res.json({
            success: true,
            message: 'Logged out successfully'
        });
    } catch (error) {
        console.error('❌ Error logging out:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to logout',
            details: error.message
        });
    }
});

// Start server
app.listen(PORT, () => {
    console.log('='.repeat(60));
    console.log(`🚀 WhatsApp Service running on port ${PORT}`);
    console.log('='.repeat(60));
    console.log('\nAvailable endpoints:');
    console.log(`  GET  http://localhost:${PORT}/health`);
    console.log(`  GET  http://localhost:${PORT}/status`);
    console.log(`  GET  http://localhost:${PORT}/qr`);
    console.log(`  POST http://localhost:${PORT}/send-message`);
    console.log(`  POST http://localhost:${PORT}/notify-order-deletion`);
    console.log(`  POST http://localhost:${PORT}/logout`);
    console.log('='.repeat(60));
    console.log('\n📱 Initializing WhatsApp Client...\n');
    
    initializeWhatsApp();
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n⚠️ Shutting down gracefully...');
    if (client) {
        await client.destroy();
    }
    process.exit(0);
});
