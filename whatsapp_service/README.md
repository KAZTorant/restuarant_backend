# WhatsApp Web Service for Restaurant Backend

This is a Node.js service that connects to WhatsApp Web using `whatsapp-web.js` library. It provides a REST API that the Django backend can use to send WhatsApp notifications.

## Features

- 📱 WhatsApp Web integration (no third-party API needed)
- 🔐 QR code authentication
- 💾 Persistent session (stays logged in)
- 🔄 Auto-reconnect on disconnect
- 🚀 REST API for sending messages
- 📊 Health check and status endpoints

## Installation

1. **Install Node.js** (if not already installed):
   ```bash
   # On macOS
   brew install node
   
   # Or download from https://nodejs.org/
   ```

2. **Install dependencies**:
   ```bash
   cd whatsapp_service
   npm install
   ```

## Usage

### Start the Service

```bash
npm start
```

Or for development with auto-reload:
```bash
npm run dev
```

### First Time Setup

1. Start the service
2. A QR code will appear in the terminal
3. Open WhatsApp on your phone
4. Go to Settings → Linked Devices → Link a Device
5. Scan the QR code displayed in the terminal
6. The service will authenticate and stay connected

**Note**: You only need to scan the QR code once. The session is saved and will persist across restarts.

## API Endpoints

### 1. Health Check
```bash
GET http://localhost:3001/health
```

Response:
```json
{
  "status": "running",
  "whatsapp_ready": true,
  "timestamp": "2026-02-15T10:30:00.000Z"
}
```

### 2. Get Status
```bash
GET http://localhost:3001/status
```

Response:
```json
{
  "ready": true,
  "qr_code": null,
  "message": "WhatsApp is connected and ready"
}
```

### 3. Get QR Code
```bash
GET http://localhost:3001/qr
```

Response:
```json
{
  "success": true,
  "qr_code": "1@ABC123..."
}
```

### 4. Send Message
```bash
POST http://localhost:3001/send-message
Content-Type: application/json

{
  "phone": "501234567",
  "message": "Hello from restaurant!"
}
```

### 5. Send Order Deletion Notification
```bash
POST http://localhost:3001/notify-order-deletion
Content-Type: application/json

{
  "owner_phone": "501234567",
  "admin_name": "John Doe",
  "table_name": "Table 5",
  "order_id": 123,
  "meal_name": "Pizza Margherita",
  "quantity": 2,
  "price": 30.00,
  "reason_display": "Geri qaytarma",
  "comment": "Customer complaint"
}
```

### 6. Logout
```bash
POST http://localhost:3001/logout
```

## Phone Number Format

The service accepts phone numbers in various formats:
- `501234567` - Will add Azerbaijan country code (994)
- `994501234567` - Full format with country code
- `+994501234567` - International format

All formats are automatically normalized.

## Configuration

You can configure the port via environment variable:

```bash
WHATSAPP_SERVICE_PORT=3001 npm start
```

Or create a `.env` file:
```
WHATSAPP_SERVICE_PORT=3001
```

## Session Management

- Session data is stored in `./whatsapp-session/` directory
- This keeps you logged in across restarts
- To logout and reset: Use the `/logout` endpoint or delete the `whatsapp-session` folder

## Troubleshooting

### QR Code not appearing
- Wait a few seconds, it takes time to initialize
- Check terminal output for errors
- Ensure no firewall is blocking the connection

### "WhatsApp is not ready" error
- Check if QR code was scanned
- Visit `http://localhost:3001/status` to check connection status
- Restart the service and scan QR code again

### Message not sending
- Verify the phone number format
- Ensure WhatsApp is connected (check status endpoint)
- Check if the recipient has WhatsApp installed

### Session expired
- Delete the `whatsapp-session` folder
- Restart the service
- Scan the QR code again

## Running as a Background Service

### Using PM2 (Recommended)

1. Install PM2:
   ```bash
   npm install -g pm2
   ```

2. Start service:
   ```bash
   pm2 start server.js --name whatsapp-service
   ```

3. Save configuration:
   ```bash
   pm2 save
   pm2 startup
   ```

4. Manage service:
   ```bash
   pm2 status
   pm2 logs whatsapp-service
   pm2 restart whatsapp-service
   pm2 stop whatsapp-service
   ```

### Using systemd (Linux)

Create `/etc/systemd/system/whatsapp-service.service`:
```ini
[Unit]
Description=WhatsApp Service for Restaurant
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/whatsapp_service
ExecStart=/usr/bin/node server.js
Restart=always
Environment=NODE_ENV=production
Environment=WHATSAPP_SERVICE_PORT=3001

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable whatsapp-service
sudo systemctl start whatsapp-service
sudo systemctl status whatsapp-service
```

## Security Notes

- 🔒 This service should run on a trusted server only
- 🚫 Don't expose it directly to the internet
- 🔐 Use a reverse proxy (nginx) with authentication if needed
- 📱 Only authorized restaurant staff should scan the QR code
- 🔑 Consider adding API key authentication for production

## Maintenance

### Clear Session and Re-authenticate
```bash
rm -rf whatsapp-session/
npm start
# Scan QR code again
```

### Update Dependencies
```bash
npm update
```

### Check Logs
```bash
# If using PM2
pm2 logs whatsapp-service

# If running directly
# Logs appear in terminal
```
