# WhatsApp Order Item Deletion Notification Integration

## Overview

This document describes the WhatsApp notification system that alerts the restaurant owner when confirmed order items are deleted from orders. The system sends real-time notifications via WhatsApp Web integration whenever an admin/waitress removes items from confirmed orders.

## Features

- **Real-time Notifications**: Instant WhatsApp messages when order items are deleted
- **Detailed Information**: Includes admin name, room, table, order details, meal info, reason, and comments
- **Azerbaijani Language Support**: All notifications are in Azerbaijani
- **Reason Tracking**: Distinguishes between returns ("Geri qaytarma") and waste ("İsraf/Tullantı")
- **Silent Failure**: If WhatsApp service is not configured, the system continues without breaking order operations

## Prerequisites

Before setting up on a new PC, ensure you have:

1. **Node.js** (v14 or higher)
2. **Python 3.9+** with virtual environment
3. **WhatsApp Business Account** or personal WhatsApp number
4. **Access to scan QR code** for WhatsApp Web authentication

## Installation Steps

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd restuarant_backend
```

### 2. Backend Setup (Django)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Install Python dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (if needed)
python manage.py createsuperuser
```

### 3. WhatsApp Service Setup

```bash
# Navigate to WhatsApp service directory
cd whatsapp_service

# Install Node.js dependencies
npm install

# Start WhatsApp service
npm start
```

### 4. WhatsApp Authentication

When you start the WhatsApp service for the first time:

1. A QR code will be displayed in the terminal
2. Open WhatsApp on your phone
3. Go to **Settings** → **Linked Devices** → **Link a Device**
4. Scan the QR code displayed in the terminal
5. Once authenticated, the session will be saved in `whatsapp_service/whatsapp-session/`

### 5. Configure Owner Phone Number

Edit `whatsapp_service/server.js` and set the owner's phone number:

```javascript
// Owner's phone number in international format (without + or spaces)
const OWNER_PHONE = '994xxxxxxxxx'; // Replace with actual number
```

**Phone Number Format:**
- Country code + number (no spaces, no +)
- Example for Azerbaijan: `994501234567`
- Example for Turkey: `905xxxxxxxxx`

### 6. Start Both Services

Open two terminal windows:

**Terminal 1 - Django Backend:**
```bash
cd restuarant_backend
source venv/bin/activate
python manage.py runserver
```

**Terminal 2 - WhatsApp Service:**
```bash
cd restuarant_backend/whatsapp_service
npm start
```

## Configuration Files

### `whatsapp_service/package.json`

```json
{
  "name": "restaurant-whatsapp-service",
  "version": "1.0.0",
  "description": "WhatsApp notification service for restaurant",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "whatsapp-web.js": "^1.23.0",
    "qrcode-terminal": "^0.12.0",
    "express": "^4.18.2"
  }
}
```

### `whatsapp_service/server.js`

The service runs on port **3001** and provides the following endpoints:

- `GET /health` - Check if service is running
- `GET /status` - Check WhatsApp connection status
- `POST /notify/order-item-deleted` - Send order deletion notifications

### Environment Variables (Optional)

Create a `.env` file in the `whatsapp_service` directory:

```env
PORT=3001
OWNER_PHONE=994xxxxxxxxx
```

## Django Integration

### File: `apps/commons/utils/whatsapp.py`

This utility module provides the WhatsApp notification interface:

```python
class WhatsAppNotifier:
    def __init__(self):
        self.base_url = 'http://localhost:3001'
    
    def is_configured(self):
        """Check if WhatsApp service is ready"""
        # Returns True if service is running and authenticated
    
    def notify_order_item_deleted(self, order_item_info):
        """Send notification when order item is deleted"""
        # Sends POST request to /notify/order-item-deleted
```

### File: `apps/orders/apis/order_items/remove.py`

The delete order item API automatically sends notifications:

```python
@staticmethod
def _send_whatsapp_notification(order, order_item, reason, comment, user):
    """Send WhatsApp notification to restaurant owner"""
    try:
        whatsapp = get_whatsapp_notifier()
        
        if not whatsapp.is_configured():
            logger.warning("WhatsApp service not ready. Skipping notification.")
            return  # Silent failure
        
        order_item_info = {
            'admin_name': user.get_full_name() or user.username,
            'room_name': order.table.room.name if order.table and order.table.room else 'N/A',
            'table_number': order.table.number if order.table else 'N/A',
            'order_id': order.id,
            'order_created_at': order.created_at.strftime('%d.%m.%Y %H:%M'),
            'deleted_at': timezone.now().strftime('%d.%m.%Y %H:%M'),
            'meal_name': order_item.meal.name,
            'quantity': 1 if order_item.quantity > 1 else order_item.quantity,
            'price': order_item.meal.price if order_item.quantity > 1 else order_item.price,
            'reason': reason,
            'reason_display': reason_display_map.get(reason, reason),
            'comment': comment or '',
        }
        
        whatsapp.notify_order_item_deleted(order_item_info)
        
    except Exception as e:
        logger.error(f"Failed to send WhatsApp notification: {e}")
        # Order deletion continues even if notification fails
```

## Notification Message Format

When an order item is deleted, the owner receives a WhatsApp message in this format:

```
🚨 SİFARİŞ MƏHSULU SİLİNDİ

👤 Admin: [Admin Name]
🏠 Otaq: [Room Name]
🪑 Masa: [Table Number]

📋 Sifariş ID: [Order ID]
🕐 Sifariş yaradılma: [DD.MM.YYYY HH:MM]
🕐 Silinmə vaxtı: [DD.MM.YYYY HH:MM]

🍽 Məhsul: [Meal Name]
📊 Miqdar: [Quantity]
💰 Qiymət: [Price] AZN

❗️ Səbəb: [Reason Display]
💬 Qeyd: [Comment]
```

### Example Message:

```
🚨 SİFARİŞ MƏHSULU SİLİNDİ

👤 Admin: Kamran Hacili
🏠 Otaq: Main Hall
🪑 Masa: 5

📋 Sifariş ID: 12345
🕐 Sifariş yaradılma: 27.02.2026 14:30
🕐 Silinmə vaxtı: 27.02.2026 15:45

🍽 Məhsul: Chicken Kebab
📊 Miqdar: 2
💰 Qiymət: 25.00 AZN

❗️ Səbəb: Geri qaytarma
💬 Qeyd: Müştəri allergiyası var
```

## Testing

### 1. Test WhatsApp Service Status

```bash
curl http://localhost:3001/status
```

Expected response:
```json
{
  "status": "ready",
  "authenticated": true
}
```

### 2. Test Order Item Deletion

Use Django admin or API to delete a confirmed order item:

```bash
curl -X DELETE http://localhost:8000/api/orders/delete-item/[table_id]/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 12345,
    "meal_id": 67,
    "confirmed": true,
    "reason": "return",
    "reason_comment": "Customer allergy"
  }'
```

The owner should receive a WhatsApp notification immediately.

## Troubleshooting

### WhatsApp Service Not Starting

**Problem:** Service fails to start or crashes

**Solutions:**
- Check Node.js is installed: `node --version`
- Delete `whatsapp_service/whatsapp-session/` and re-authenticate
- Check port 3001 is not in use: `lsof -i :3001`
- Check logs in terminal for specific errors

### QR Code Not Displayed

**Problem:** QR code doesn't appear in terminal

**Solutions:**
- Ensure terminal supports QR code display
- Try clearing terminal and restarting service
- Check `qrcode-terminal` package is installed

### Notifications Not Received

**Problem:** WhatsApp messages not being sent

**Solutions:**
1. Check WhatsApp service is running: `curl http://localhost:3001/health`
2. Verify phone number format in `server.js` (no + or spaces)
3. Ensure WhatsApp session is authenticated: `curl http://localhost:3001/status`
4. Check Django logs for errors
5. Verify owner's phone number is registered with WhatsApp

### Authentication Expired

**Problem:** "Session ended" or authentication lost

**Solutions:**
- Delete `whatsapp_service/whatsapp-session/`
- Restart WhatsApp service
- Scan QR code again
- Keep WhatsApp Web session active

### Connection Issues

**Problem:** Django can't connect to WhatsApp service

**Solutions:**
- Verify both services are running
- Check firewall settings
- Ensure port 3001 is accessible
- Try `curl http://localhost:3001/health` from Django server

## Production Deployment

### Using PM2 (Process Manager)

```bash
# Install PM2 globally
npm install -g pm2

# Start WhatsApp service with PM2
cd whatsapp_service
pm2 start server.js --name whatsapp-service

# Auto-restart on system reboot
pm2 startup
pm2 save

# View logs
pm2 logs whatsapp-service

# Restart service
pm2 restart whatsapp-service
```

### Using Systemd (Linux)

Create `/etc/systemd/system/whatsapp-service.service`:

```ini
[Unit]
Description=WhatsApp Notification Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/restaurant_backend/whatsapp_service
ExecStart=/usr/bin/node server.js
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable whatsapp-service
sudo systemctl start whatsapp-service
sudo systemctl status whatsapp-service
```

### Environment Variables for Production

```env
NODE_ENV=production
PORT=3001
OWNER_PHONE=994xxxxxxxxx
LOG_LEVEL=info
```

## Security Considerations

1. **Session Storage**: Keep `whatsapp-session/` directory secure and backed up
2. **API Access**: Consider adding authentication to WhatsApp service endpoints
3. **Network**: Use HTTPS in production
4. **Phone Numbers**: Store sensitive phone numbers in environment variables
5. **Logs**: Don't log sensitive customer information

## Backup and Recovery

### Backup WhatsApp Session

```bash
# Backup session directory
tar -czf whatsapp-session-backup.tar.gz whatsapp_service/whatsapp-session/

# Restore session
tar -xzf whatsapp-session-backup.tar.gz
```

### Re-authentication Process

If you lose the session or need to re-authenticate:

1. Stop WhatsApp service
2. Delete `whatsapp_service/whatsapp-session/`
3. Start WhatsApp service
4. Scan new QR code
5. Verify with test notification

## API Reference

### POST /notify/order-item-deleted

Send order item deletion notification to owner.

**Request Body:**
```json
{
  "admin_name": "Kamran Hacili",
  "room_name": "Main Hall",
  "table_number": "5",
  "order_id": 12345,
  "order_created_at": "27.02.2026 14:30",
  "deleted_at": "27.02.2026 15:45",
  "meal_name": "Chicken Kebab",
  "quantity": 2,
  "price": "25.00",
  "reason": "return",
  "reason_display": "Geri qaytarma",
  "comment": "Müştəri allergiyası var"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Notification sent successfully"
}
```

## Support

For issues or questions:
1. Check this documentation
2. Review error logs in both Django and WhatsApp service
3. Test connectivity between services
4. Verify WhatsApp authentication status

## Version History

- **v1.0.0** (February 2026) - Initial implementation
  - Order item deletion notifications
  - Azerbaijani language support
  - Reason and comment tracking
  - Silent failure mode

## Related Documentation

- [WHATSAPP_IMPLEMENTATION_SUMMARY.md](./WHATSAPP_IMPLEMENTATION_SUMMARY.md)
- [WHATSAPP_SETUP.md](./WHATSAPP_SETUP.md)
- [WHATSAPP_NOTIFICATION_README.md](./WHATSAPP_NOTIFICATION_README.md)

---

**Last Updated:** February 27, 2026
