"""
WhatsApp Notification Utility
Communicates with the WhatsApp Web service to send notifications
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    """
    Handles WhatsApp notifications via the WhatsApp Web service
    """
    
    def __init__(self):
        self.service_url = getattr(settings, 'WHATSAPP_SERVICE_URL', 'http://localhost:3000')
        self.owner_phone = getattr(settings, 'RESTAURANT_OWNER_PHONE', None)
        self.timeout = 10  # seconds
    
    def is_configured(self):
        """Check if WhatsApp service is configured and ready"""
        if not self.owner_phone:
            logger.warning("Restaurant owner phone not configured")
            return False
        
        try:
            response = requests.get(
                f"{self.service_url}/status",
                timeout=self.timeout
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('ready', False)
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"WhatsApp service not reachable: {e}")
            return False
    
    def get_status(self):
        """Get WhatsApp service status"""
        try:
            response = requests.get(
                f"{self.service_url}/status",
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            return {'ready': False, 'error': 'Service unavailable'}
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get status: {e}")
            return {'ready': False, 'error': str(e)}
    
    def send_message(self, phone, message):
        """
        Send a WhatsApp message
        
        Args:
            phone (str): Recipient's phone number (format: 501234567 or 994501234567)
            message (str): Message content
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            response = requests.post(
                f"{self.service_url}/send-message",
                json={
                    'phone': phone,
                    'message': message
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"WhatsApp message sent to {phone}")
                    return True
                else:
                    logger.error(f"Failed to send message: {data.get('error')}")
                    return False
            else:
                logger.error(f"WhatsApp service error: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False
    
    def notify_order_item_deleted(self, order_item_info):
        """
        Send notification to restaurant owner when an order item is deleted
        
        Args:
            order_item_info (dict): Dictionary containing order item details
                - admin_name: Name of admin who deleted the item
                - room_name: Room/hall name
                - table_number: Table number
                - order_id: Order ID
                - order_created_at: When the order was created
                - deleted_at: When the item was deleted
                - meal_name: Name of the meal
                - quantity: Quantity deleted
                - price: Price of deleted item(s)
                - reason: Reason for deletion (return/waste)
                - reason_display: Display text for reason
                - comment: Additional comment
        """
        if not self.owner_phone:
            logger.warning("Restaurant owner phone not configured. Cannot send notification.")
            return False
        
        try:
            response = requests.post(
                f"{self.service_url}/notify-order-deletion",
                json={
                    'owner_phone': self.owner_phone,
                    'admin_name': order_item_info.get('admin_name', 'N/A'),
                    'room_name': order_item_info.get('room_name', 'N/A'),
                    'table_number': order_item_info.get('table_number', 'N/A'),
                    'order_id': order_item_info.get('order_id', 'N/A'),
                    'order_created_at': order_item_info.get('order_created_at', 'N/A'),
                    'deleted_at': order_item_info.get('deleted_at', 'N/A'),
                    'meal_name': order_item_info.get('meal_name', 'N/A'),
                    'quantity': order_item_info.get('quantity', 0),
                    'price': float(order_item_info.get('price', 0)),
                    'reason_display': order_item_info.get('reason_display', 'N/A'),
                    'comment': order_item_info.get('comment', '')
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"Order deletion notification sent to owner")
                    return True
                else:
                    logger.error(f"Failed to send notification: {data.get('error')}")
                    return False
            else:
                logger.error(f"WhatsApp service error: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send order deletion notification: {e}")
            return False


# Singleton instance
_whatsapp_notifier = None


def get_whatsapp_notifier():
    """Get or create WhatsApp notifier singleton instance"""
    global _whatsapp_notifier
    if _whatsapp_notifier is None:
        _whatsapp_notifier = WhatsAppNotifier()
    return _whatsapp_notifier
    return _whatsapp_notifier
