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
        self.timeout = 10  # seconds
        
        # Get owner phones from database (preferred) or fallback to settings
        self.owner_phones = self._get_owner_phones()
        
        # Backward compatibility: keep single phone as primary
        self.owner_phone = self.owner_phones[0] if self.owner_phones else None
    
    def _get_owner_phones(self):
        """
        Get active owner phone numbers from database.
        Falls back to settings.RESTAURANT_OWNER_PHONE if DB is empty.
        
        Returns:
            list: List of active phone numbers
        """
        try:
            # Import here to avoid circular dependency
            from apps.users.models import WhatsAppConfig

            # Get active phones from DB
            phones = list(
                WhatsAppConfig.objects
                .filter(is_active=True)
                .values_list('phone', flat=True)
                .order_by('created_at')
            )
            
            if phones:
                logger.info(f"Loaded {len(phones)} active WhatsApp phone(s) from database: {phones}")
                return phones
            
            # Fallback to settings if DB is empty
            logger.warning("No active WhatsApp phones in database. Falling back to settings.")
            
        except Exception as e:
            # If DB not ready or model doesn't exist yet (migrations)
            logger.warning(f"Could not load WhatsApp phones from database: {e}. Using settings.")
        
        # Fallback to settings
        owner_phone_raw = getattr(settings, 'RESTAURANT_OWNER_PHONE', None)
        if owner_phone_raw:
            phones = [p.strip() for p in owner_phone_raw.split(',') if p.strip()]
            if phones:
                logger.info(f"Using WhatsApp phone(s) from settings: {phones}")
                return phones
        
        logger.warning("No WhatsApp owner phones configured in database or settings.")
        return []
    
    def is_configured(self):
        """Check if WhatsApp service is configured and ready"""
        if not self.owner_phones:
            logger.warning("Restaurant owner phone(s) not configured")
            return False
        
        url = f"{self.service_url}/health"
        try:
            logger.info(f"Checking WhatsApp service health at: {url}")
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                is_ready = data.get('whatsapp_ready', False)
                logger.info(f"WhatsApp service health check successful. Ready: {is_ready}, Response: {data}")
                return is_ready
            else:
                logger.error(
                    f"WhatsApp service health check failed.\n"
                    f"  URL: {url}\n"
                    f"  Status Code: {response.status_code}\n"
                    f"  Response: {response.text[:500]}"
                )
                return False
        except requests.exceptions.Timeout as e:
            logger.error(f"WhatsApp service timeout (>{self.timeout}s). URL: {url}, Error: {e}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"WhatsApp service connection failed. URL: {url}, Error: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"WhatsApp service request error. URL: {url}, Error: {type(e).__name__}: {e}")
            return False
    
    def get_status(self):
        """Get WhatsApp service status"""
        url = f"{self.service_url}/health"
        try:
            logger.info(f"Getting WhatsApp service status from: {url}")
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"WhatsApp status retrieved successfully: {data}")
                return {
                    'ready': data.get('whatsapp_ready', False),
                    'authenticated': data.get('whatsapp_ready', False),
                }
            else:
                error_msg = f"Service returned status {response.status_code}"
                logger.error(
                    f"WhatsApp service status check failed.\n"
                    f"  URL: {url}\n"
                    f"  Status Code: {response.status_code}\n"
                    f"  Response: {response.text[:500]}"
                )
                return {'ready': False, 'error': error_msg}
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout after {self.timeout}s"
            logger.error(f"WhatsApp service timeout. URL: {url}, Error: {e}")
            return {'ready': False, 'error': error_msg}
        except requests.exceptions.ConnectionError as e:
            error_msg = "Connection refused or service not running"
            logger.error(f"WhatsApp service connection failed. URL: {url}, Error: {e}")
            return {'ready': False, 'error': error_msg}
        except requests.exceptions.RequestException as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"WhatsApp service request error. URL: {url}, Error: {error_msg}")
            return {'ready': False, 'error': error_msg}
    
    def send_message(self, phone, message):
        """
        Send a WhatsApp message
        
        Args:
            phone (str): Recipient's phone number (format: 501234567 or 994501234567)
            message (str): Message content
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        url = f"{self.service_url}/send-message"
        payload = {'phone': phone, 'message': message}
        
        try:
            logger.info(f"Sending WhatsApp message to {phone} via {url}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"WhatsApp message sent successfully to {phone}. Response: {data}")
                    return True
                else:
                    error = data.get('error', 'Unknown error')
                    logger.error(
                        f"WhatsApp message sending failed.\n"
                        f"  URL: {url}\n"
                        f"  Phone: {phone}\n"
                        f"  Status: 200 but success=false\n"
                        f"  Error: {error}\n"
                        f"  Full Response: {data}"
                    )
                    return False
            else:
                logger.error(
                    f"WhatsApp send message request failed.\n"
                    f"  URL: {url}\n"
                    f"  Phone: {phone}\n"
                    f"  Status Code: {response.status_code}\n"
                    f"  Response: {response.text[:500]}"
                )
                return False
                
        except requests.exceptions.Timeout as e:
            logger.error(f"WhatsApp send message timeout (>{self.timeout}s). URL: {url}, Phone: {phone}, Error: {e}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"WhatsApp service connection failed while sending message. URL: {url}, Phone: {phone}, Error: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"WhatsApp send message request error. URL: {url}, Phone: {phone}, Error: {type(e).__name__}: {e}")
            return False
    
    def notify_order_item_deleted(self, order_item_info):
        """
        Send notification to restaurant owner(s) when an order item is deleted
        If multiple owner phones configured, sends to all.
        
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
        if not self.owner_phones:
            logger.warning("Restaurant owner phone(s) not configured. Cannot send notification.")
            return False
        
        url = f"{self.service_url}/notify-order-deletion"
        payload = {
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
        }
        
        # Send to all configured owner phones
        success_count = 0
        for owner_phone in self.owner_phones:
            payload['owner_phone'] = owner_phone
            
            try:
                logger.info(
                    f"Sending order deletion notification to owner.\n"
                    f"  URL: {url}\n"
                    f"  Owner Phone: {owner_phone}\n"
                    f"  Order ID: {payload['order_id']}\n"
                    f"  Meal: {payload['meal_name']}\n"
                    f"  Quantity: {payload['quantity']}"
                )
                response = requests.post(url, json=payload, timeout=self.timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        logger.info(
                            f"Order deletion notification sent successfully to {owner_phone}.\n"
                            f"  Order ID: {payload['order_id']}\n"
                            f"  Response: {data}"
                        )
                        success_count += 1
                    else:
                        error = data.get('error', 'Unknown error')
                        logger.error(
                            f"Order deletion notification failed for {owner_phone}.\n"
                            f"  URL: {url}\n"
                            f"  Order ID: {payload['order_id']}\n"
                            f"  Status: 200 but success=false\n"
                            f"  Error: {error}\n"
                            f"  Full Response: {data}"
                        )
                else:
                    logger.error(
                        f"Order deletion notification request failed for {owner_phone}.\n"
                        f"  URL: {url}\n"
                        f"  Order ID: {payload['order_id']}\n"
                        f"  Status Code: {response.status_code}\n"
                        f"  Response: {response.text[:500]}"
                    )
                    
            except requests.exceptions.Timeout as e:
                logger.error(
                    f"Order deletion notification timeout (>{self.timeout}s) for {owner_phone}.\n"
                    f"  URL: {url}\n"
                    f"  Order ID: {payload['order_id']}\n"
                    f"  Error: {e}"
                )
            except requests.exceptions.ConnectionError as e:
                logger.error(
                    f"WhatsApp service connection failed during order deletion notification for {owner_phone}.\n"
                    f"  URL: {url}\n"
                    f"  Order ID: {payload['order_id']}\n"
                    f"  Error: {e}"
                )
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Order deletion notification request error for {owner_phone}.\n"
                    f"  URL: {url}\n"
                    f"  Order ID: {payload['order_id']}\n"
                    f"  Error: {type(e).__name__}: {e}"
                )
        
        # Return True if at least one notification was sent successfully
        if success_count > 0:
            logger.info(f"Order deletion notification sent to {success_count}/{len(self.owner_phones)} owner(s)")
            return True
        else:
            logger.error(f"Failed to send order deletion notification to all {len(self.owner_phones)} owner(s)")
            return False


# Singleton instance
_whatsapp_notifier = None


def get_whatsapp_notifier():
    """Get or create WhatsApp notifier singleton instance"""
    global _whatsapp_notifier
    if _whatsapp_notifier is None:
        _whatsapp_notifier = WhatsAppNotifier()
    return _whatsapp_notifier
