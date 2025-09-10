import asyncio
import logging
from decimal import Decimal

import requests
from django.conf import settings
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more info
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RestaurantBot:
    def __init__(self, token):
        self.token = token
        self.base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        logger.info(f"Initializing bot with token: {token[:10]}...")
        logger.info(f"Base URL: {self.base_url}")
        
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Setup bot command and callback handlers"""
        logger.info("Setting up handlers...")
        
        # Add a debug handler to catch ALL messages
        async def debug_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info(f"🔍 DEBUG: Received message from user {update.effective_user.id}: '{update.message.text}'")
            await update.message.reply_text(f"🤖 Bot received: {update.message.text}")
        
        # Add handlers in this order (most specific first)
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("orders", self.orders_menu))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Add debug handler last (catches non-command text messages only)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, debug_all_messages))
        
        logger.info("Handlers set up successfully")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when /start command is issued"""
        logger.info(f"Start command received from user: {update.effective_user.id}")
        welcome_text = """
🍽️ Restoran Bot-a xoş gəldiniz!

Bu bot vasitəsilə restoranın statistikalarını izləyə bilərsiniz.

Əmrlər:
/orders - Aktiv sifarişlər
/help - Kömək

Başlamaq üçün /orders düyməsini basın.
        """
        try:
            await update.message.reply_text(welcome_text)
            logger.info("Welcome message sent successfully")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help message"""
        logger.info(f"Help command received from user: {update.effective_user.id}")
        help_text = """
🆘 Kömək

Mövcud əmrlər:
/start - Başlanğıc mesajı
/orders - Aktiv sifarişləri göstər
/help - Bu kömək mesajı

Düymələr vasitəsilə naviqasiya edə bilərsiniz.
        """
        try:
            await update.message.reply_text(help_text)
            logger.info("Help message sent successfully")
        except Exception as e:
            logger.error(f"Error sending help message: {e}")

    async def orders_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show orders menu with buttons"""
        keyboard = [
            [InlineKeyboardButton("📊 Aktiv Sifarişlər", callback_data='active_orders')],
            [InlineKeyboardButton("💰 Ödəniş Statistikası", callback_data='payment_stats')],
            [InlineKeyboardButton("🔄 Yenilə", callback_data='refresh_orders')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "📋 Sifarişlər Menyusu\n\nİstədiyiniz məlumatı seçin:"
        
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()

        if query.data == 'active_orders':
            await self.show_active_orders(query)
        elif query.data == 'payment_stats':
            await self.show_payment_stats(query)
        elif query.data == 'refresh_orders':
            await self.orders_menu(update, context)

    async def show_active_orders(self, query):
        """Fetch and display active orders"""
        try:
            # Call your Django API
            response = requests.get(f"{self.base_url}/orders/active-orders/")
            
            if response.status_code == 200:
                data = response.json()
                
                message = f"""
📊 Aktiv Sifarişlər

💰 Ödəniş Növləri:
├ 💵 Nağd: {data['cash_total']:.2f} AZN
├ 💳 Kart: {data['card_total']:.2f} AZN
├ 🔄 Digər: {data['other_total']:.2f} AZN
└ ❌ Ödənilməmiş: {data['unpaid_total']:.2f} AZN

🔄 Yenilənmə vaxtı: {self.get_current_time()}
                """
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Yenilə", callback_data='active_orders')],
                    [InlineKeyboardButton("⬅️ Geri", callback_data='refresh_orders')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ Məlumat alınarkən xəta baş verdi.")
                
        except Exception as e:
            logger.error(f"Error fetching active orders: {e}")
            await query.edit_message_text("❌ Serverlə əlaqə yaradılmadı.")

    async def show_payment_stats(self, query):
        """Show detailed payment statistics"""
        try:
            response = requests.get(f"{self.base_url}/orders/active-orders/")
            
            if response.status_code == 200:
                data = response.json()
                
                total_paid = data['cash_total'] + data['card_total'] + data['other_total']
                total_all = total_paid + data['unpaid_total']
                
                message = f"""
💰 Ödəniş Statistikası

📈 Ümumi Məlumat:
├ Ümumi: {total_all:.2f} AZN
├ Ödənilmiş: {total_paid:.2f} AZN
└ Ödənilməmiş: {data['unpaid_total']:.2f} AZN

📊 Ödəniş Növləri:
├ 💵 Nağd: {data['cash_total']:.2f} AZN ({self.get_percentage(data['cash_total'], total_paid):.1f}%)
├ 💳 Kart: {data['card_total']:.2f} AZN ({self.get_percentage(data['card_total'], total_paid):.1f}%)
└ 🔄 Digər: {data['other_total']:.2f} AZN ({self.get_percentage(data['other_total'], total_paid):.1f}%)

🔄 Yenilənmə: {self.get_current_time()}
                """
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Yenilə", callback_data='payment_stats')],
                    [InlineKeyboardButton("⬅️ Geri", callback_data='refresh_orders')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ Məlumat alınarkən xəta baş verdi.")
                
        except Exception as e:
            logger.error(f"Error fetching payment stats: {e}")
            await query.edit_message_text("❌ Serverlə əlaqə yaradılmadı.")

    def get_percentage(self, part, total):
        """Calculate percentage"""
        if total == 0:
            return 0
        return (part / total) * 100

    def get_current_time(self):
        """Get current time formatted"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def run(self):
        """Start the bot (synchronous method)"""
        logger.info("Starting Restaurant Bot...")
        
        # Use the synchronous run_polling method
        self.application.run_polling(drop_pending_updates=True)

# Bot instance
bot_instance = None

def get_bot():
    """Get bot instance"""
    global bot_instance
    if bot_instance is None:
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if token:
            bot_instance = RestaurantBot(token)
    return bot_instance