import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.orders.telegram_bot.bot import get_bot


@csrf_exempt
@require_POST
def webhook(request):
    """Webhook endpoint for Telegram"""
    try:
        bot = get_bot()
        if bot:
            update_data = json.loads(request.body)
            # Process webhook update
            # This is for production webhook setup
            pass
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def bot_status(request):
    """Check bot status"""
    bot = get_bot()
    return JsonResponse({
        'status': 'active' if bot else 'inactive',
        'message': 'Bot is running' if bot else 'Bot not configured'
    })