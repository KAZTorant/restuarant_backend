from django.conf import settings

# Bot configuration
BOT_CONFIG = {
    'TOKEN': getattr(settings, 'TELEGRAM_BOT_TOKEN', ''),
    'ALLOWED_USERS': getattr(settings, 'TELEGRAM_ALLOWED_USERS', []),
    'API_BASE_URL': getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000'),
    'WEBHOOK_URL': getattr(settings, 'TELEGRAM_WEBHOOK_URL', ''),
}

# Messages
MESSAGES = {
    'WELCOME': '🍽️ Restoran Bot-a xoş gəldiniz!',
    'UNAUTHORIZED': '❌ Bu botu istifadə etmək üçün icazəniz yoxdur.',
    'ERROR': '❌ Xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.',
    'NO_DATA': '📊 Hal-hazırda məlumat yoxdur.',
}