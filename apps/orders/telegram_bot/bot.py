import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal

import requests
from django.conf import settings
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters
)

# Import AI analyze command
from apps.bot.business_owner.commands.ai_analyze import AIAnalyzeCommand

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

        # Add handlers in this order (most specific first)
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(
            CommandHandler("orders", self.orders_menu))
        self.application.add_handler(
            CommandHandler("ai_analyze", AIAnalyzeCommand.handle_command))
        self.application.add_handler(
            CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_text_input))

        logger.info("Handlers set up successfully")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when /start command is issued"""
        logger.info(
            f"Start command received from user: {update.effective_user.id}")
        welcome_text = """<b>🍽️ RESTORAN BOT-A XOŞ GƏLDİNİZ!</b>

📊 Bu bot vasitəsilə restoranın sifariş hesabatlarını izləyə bilərsiniz.

<b>🔧 MÖVCUD ƏMRLƏR:</b>
• 📈 /orders - Sifariş hesabatları
• 🤖 /ai_analyze - AI analitik asistanı
• ❓ /help - Kömək məlumatları

<i>🚀 Başlamaq üçün /orders düyməsini basın.</i>"""
        try:
            await update.message.reply_text(welcome_text, parse_mode='HTML')
            logger.info("Welcome message sent successfully")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help message"""
        logger.info(
            f"Help command received from user: {update.effective_user.id}")
        help_text = """<b>🆘 KÖMƏK MƏLUMATİ</b>

<b>📋 MÖVCUD ƏMRLƏR:</b>
• 🏠 /start - Başlanğıc mesajı
• 📊 /orders - Sifariş hesabatlarını göstər
• 🤖 /ai_analyze - AI analitik asistanı
• ❓ /help - Bu kömək mesajı

<b>🧭 NAVİQASİYA:</b>
• Düymələr vasitəsilə naviqasiya edə bilərsiniz
• Hər səhifədə "Geri" düyməsi mövcuddur

<b>🤖 AI ANALİTİK:</b>
• Natural dildə suallar verin
• Avtomatik məlumat analizi alın
• Satış, menyu və sifarişlər haqqında məlumat

<i>💡 Suallarınız varsa /orders və ya /ai_analyze ilə başlayın.</i>"""
        try:
            await update.message.reply_text(help_text, parse_mode='HTML')
            logger.info("Help message sent successfully")
        except Exception as e:
            logger.error(f"Error sending help message: {e}")

    async def orders_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show orders menu with main options"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "📈 Günün Hesabatı",
                    callback_data='daily_report'
                )
            ],
            [
                InlineKeyboardButton(
                    "📆 Tarix/Vaxt Aralığı",
                    callback_data='date_range_menu'
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Ana Səhifə",
                    callback_data='main_menu'
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = """<b>📊 SİFARİŞ HESABATLARI</b>

<b>📈 GÜNÜN HESABATI</b>
İş dövrünün sifariş statistikaları

<b>📆 TARİX ARALIĞI</b>
Seçdiyiniz dövrün sifarişləri

<i>İstədiyiniz hesabat növünü seçin:</i>"""

        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await self.safe_edit_message(update.callback_query, text, reply_markup, parse_mode='HTML')

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()

        if query.data == 'daily_report':
            await self.show_daily_report_menu(query)
        elif query.data.startswith('period_report_'):
            date_str = query.data.replace('period_report_', '')
            await self.show_period_report(query, date_str)
        elif query.data == 'date_range_menu':
            await self.show_date_range_menu(query)
        elif query.data == 'main_menu':
            AIAnalyzeCommand.deactivate_ai_analyze(context)
            await self.orders_menu(update, context)
        elif query.data.startswith('date_range_'):
            await self.handle_date_range_selection(query)
        elif query.data == 'daily_report_other':
            await self.request_daily_custom_date_input(query)
        elif query.data.startswith('refresh_single_date_'):
            await self.handle_refresh_single_date(query)
        elif query.data.startswith('refresh_date_range_'):
            await self.handle_refresh_date_range(query)
        elif query.data == 'cancel_ai_analyze':
            AIAnalyzeCommand.deactivate_ai_analyze(context)
            await AIAnalyzeCommand.handle_cancel(query)
        elif query.data == 'new_ai_analyze':
            await AIAnalyzeCommand.handle_command(update, context)

    async def show_today_report(self, query):
        """Show today's order report"""
        try:
            # Get today's date in YYYY-MM-DD format
            today = date.today().isoformat()

            # Call API for today's orders
            response = requests.get(
                f"{self.base_url}/orders/active-orders/?date={today}")

            if response.status_code == 200:
                data = response.json()

                message = f"""<b>📅 Bugünkü Hesabat ({today})</b>

<pre>
┌─────────────────────────────────┐
│         ÖDƏNİŞ STATİSTİKASI     │
├─────────────────────────────────┤
│ 💵 Nağd        │ {data['cash_total']:>8.2f} AZN │
│ 💳 Kart        │ {data['card_total']:>8.2f} AZN │
│ 🔄 Digər       │ {data['other_total']:>8.2f} AZN │
│ ❌ Ödənilməmiş │ {data['unpaid_total']:>8.2f} AZN │
├─────────────────────────────────┤
│         ÜMUMİ MƏBLƏĞ            │
├─────────────────────────────────┤
│ ✅ Ödənilmiş   │ {data['paid_total']:>8.2f} AZN │
│ 📊 Toplam      │ {(data['paid_total'] + data['unpaid_total']):>8.2f} AZN │
└─────────────────────────────────┘
</pre>

🕒 <i>Yenilənmə: {self.get_current_time()}</i>"""

                keyboard = [
                    [InlineKeyboardButton(
                        "🔄 Yenilə", callback_data='today_report')],
                    [InlineKeyboardButton(
                        "⬅️ Geri", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await self.safe_edit_message(query, message, reply_markup, parse_mode='HTML')
            else:
                await self.safe_edit_message(query, "<b>❌ Məlumat alınarkən xəta baş verdi.</b>", parse_mode='HTML')

        except Exception as e:
            logger.error(f"Error fetching today's report: {e}")
            await self.safe_edit_message(query, "<b>❌ Serverlə əlaqə yaradılmadı.</b>", parse_mode='HTML')

    async def show_daily_report_menu(self, query):
        """Show date selection menu for daily reports based on report start dates"""
        try:
            from datetime import date, timedelta, datetime, time
            import requests

            # Determine the correct "today" based on work period
            current_time = datetime.now().time()
            calendar_today = date.today()

            # Get work period config to determine actual "today"
            try:
                # First, try to get active config from API call
                temp_response = requests.get(
                    f"{self.base_url}/orders/period-report/?date={calendar_today.strftime('%Y-%m-%d')}")
                if temp_response.status_code == 200:
                    temp_data = temp_response.json()
                    if 'error' not in temp_data:
                        # Parse work period start time (convert to local timezone)
                        from django.utils import timezone as django_timezone
                        period_start = datetime.fromisoformat(
                            temp_data['period_start'].replace('Z', '+00:00'))
                        period_start_local = django_timezone.localtime(
                            period_start)
                        work_start_time = period_start_local.time()

                        # If current time is before work start time, we're still in previous day's work period
                        if current_time < work_start_time:
                            actual_today = calendar_today - timedelta(days=1)
                        else:
                            actual_today = calendar_today
                    else:
                        actual_today = calendar_today
                else:
                    actual_today = calendar_today
            except:
                # Fallback to calendar today if API fails
                actual_today = calendar_today

            # Get last 7 report dates starting from actual today
            report_dates = []

            # Generate potential dates and check which ones have valid reports
            for i in range(7):
                check_date = actual_today - timedelta(days=i)
                date_str = check_date.strftime('%Y-%m-%d')

                # Call API to get report info (this will create report if needed)
                try:
                    response = requests.get(
                        f"{self.base_url}/orders/period-report/?date={date_str}")
                    if response.status_code == 200:
                        data = response.json()
                        if 'error' not in data:
                            # Parse the actual report start date (convert to local timezone)
                            from datetime import datetime
                            from django.utils import timezone as django_timezone
                            report_start = datetime.fromisoformat(
                                data['period_start'].replace('Z', '+00:00'))
                            report_start_local = django_timezone.localtime(
                                report_start)
                            report_start_date = report_start_local.date()

                            report_dates.append({
                                'api_date': date_str,  # Date to send to API
                                'report_start_date': report_start_date,  # Actual report start date
                                'display_date': report_start_date.strftime('%d.%m.%Y'),
                                'period_name': data.get('period_name', 'İş Dövrü')
                            })
                except:
                    # If API fails, still add the date
                    report_dates.append({
                        'api_date': date_str,
                        'report_start_date': check_date,
                        'display_date': check_date.strftime('%d.%m.%Y'),
                        'period_name': 'İş Dövrü'
                    })

            # Create keyboard with report start date options
            keyboard = []
            for i, report_info in enumerate(report_dates):
                display_text = report_info['display_text'] = report_info['display_date']

                # Add "Bugün" for today's report
                if i == 0:  # First item is most recent
                    display_text = f"📅 Bugün ({display_text})"
                else:
                    display_text = f"📅 {display_text}"

                keyboard.append([InlineKeyboardButton(
                    display_text,
                    callback_data=f'period_report_{report_info["api_date"]}'
                )])

            # Add Digər (Other) button
            keyboard.append([InlineKeyboardButton(
                "📝 Digər", callback_data='daily_report_other')])

            # Add back button
            keyboard.append([InlineKeyboardButton(
                "⬅️ Geri", callback_data='main_menu')])

            reply_markup = InlineKeyboardMarkup(keyboard)

            text = """<b>📈 GÜNÜN HESABATI</b>

📅 <i>Son 7 iş dövrünün hesabatları:</i>
<code>(Tarixlər iş dövrünün başlama vaxtına görədir)</code>

<b>Tarixi seçin:</b>"""

            await self.safe_edit_message(query, text, reply_markup, parse_mode='HTML')

        except Exception as e:
            logger.error(f"Error showing daily report menu: {e}")
            await self.safe_edit_message(query, "<b>❌ Menyu yüklənərkən xəta baş verdi.</b>", parse_mode='HTML')

    async def show_period_report(self, query, date_str):
        """Show period report for specific date"""
        try:
            # Call period report API with date
            response = requests.get(
                f"{self.base_url}/orders/period-report/?date={date_str}")

            if response.status_code == 200:
                data = response.json()

                # Check if there's an error
                if 'error' in data:
                    message = f"""<b>📈 Günün Hesabatı ({date_str})</b>

<b>❌ {data.get('error', 'Xəta baş verdi')}</b>"""
                    keyboard = [
                        [InlineKeyboardButton(
                            "⬅️ Geri", callback_data='daily_report')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await self.safe_edit_message(query, message, reply_markup, parse_mode='HTML')
                    return

                # Parse datetime strings for display (convert to local timezone)
                from datetime import datetime
                from django.utils import timezone as django_timezone
                period_start = datetime.fromisoformat(
                    data['period_start'].replace('Z', '+00:00'))
                period_end = datetime.fromisoformat(
                    data['period_end'].replace('Z', '+00:00'))
                period_start_local = django_timezone.localtime(period_start)
                period_end_local = django_timezone.localtime(period_end)

                # Format date display
                display_date = datetime.strptime(
                    date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
                time_range = f"({period_start_local.strftime('%H:%M')} - {period_end_local.strftime('%H:%M')})"

                message = f"""<b>📈 GÜNÜN HESABATI</b>
📅 {display_date} {time_range}
📋 Dövrü: <i>{data['period_name']}</i>

<pre>
┌─────────────────────────────────┐
│         ÖDƏNİŞ STATİSTİKASI     │
├─────────────────────────────────┤
│ 💵 Nağd        │ {data['cash_total']:>8.2f} AZN │
│ 💳 Kart        │ {data['card_total']:>8.2f} AZN │
│ 🔄 Digər       │ {data['other_total']:>8.2f} AZN │
│ ❌ Ödənilməmiş │ {data['unpaid_total']:>8.2f} AZN │
├─────────────────────────────────┤
│         ÜMUMİ MƏBLƏĞ            │
├─────────────────────────────────┤
│ ✅ Ödənilmiş   │ {data['paid_total']:>8.2f} AZN │
│ 📊 Toplam      │ {(data['paid_total'] + data['unpaid_total']):>8.2f} AZN │
└─────────────────────────────────┘
</pre>

🕒 <i>Yenilənmə: {self.get_current_time()}</i>"""

                keyboard = [
                    [InlineKeyboardButton(
                        "🔄 Hesabatı Yenilə", callback_data=f'period_report_{date_str}')],
                    [InlineKeyboardButton(
                        "⬅️ Geri Qayıt", callback_data='daily_report')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await self.safe_edit_message(query, message, reply_markup, parse_mode='HTML')
            else:
                await self.safe_edit_message(query, "<b>❌ Məlumat alınarkən xəta baş verdi.</b>", parse_mode='HTML')

        except Exception as e:
            logger.error(f"Error fetching period report for {date_str}: {e}")
            await self.safe_edit_message(query, "<b>❌ Serverlə əlaqə yaradılmadı.</b>", parse_mode='HTML')

    async def show_date_range_menu(self, query):
        """Show date range selection menu"""
        keyboard = [
            [InlineKeyboardButton(
                "📅 Bu həftə", callback_data='date_range_this_week')],
            [InlineKeyboardButton(
                "📅 Keçən həftə", callback_data='date_range_last_week')],
            [InlineKeyboardButton(
                "📅 Bu ay", callback_data='date_range_this_month')],
            [InlineKeyboardButton("📝 Əl ilə daxil et",
                                  callback_data='date_range_manual')],
            [InlineKeyboardButton("⬅️ Geri", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = """<b>📆 TARİX/VAXT ARALIĞI</b>

<b>📅 HAZIR SEÇİMLƏR:</b>
• Bu həftə - Bu həftənin sifarişləri
• Keçən həftə - Keçən həftənin sifarişləri  
• Bu ay - Bu ayın sifarişləri

<b>📝 FƏRDI SEÇİM:</b>
• Əl ilə daxil et - Özünüz tarix seçin

<i>Seçiminizi edin:</i>"""

        await self.safe_edit_message(query, text, reply_markup, parse_mode='HTML')

    async def handle_date_range_selection(self, query):
        """Handle predefined date range selections"""
        try:
            from datetime import timedelta

            today = date.today()
            start_date = None
            end_date = None
            range_name = ""

            logger.info(f"Processing date range selection: {query.data}")

            if query.data == 'date_range_this_week':
                # Monday to Sunday of current week
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
                range_name = "Bu həftə"

            elif query.data == 'date_range_last_week':
                # Monday to Sunday of last week
                start_date = today - timedelta(days=today.weekday() + 7)
                end_date = start_date + timedelta(days=6)
                range_name = "Keçən həftə"

            elif query.data == 'date_range_this_month':
                # First day to last day of current month
                start_date = today.replace(day=1)
                if today.month == 12:
                    end_date = today.replace(
                        year=today.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end_date = today.replace(
                        month=today.month + 1, day=1) - timedelta(days=1)
                range_name = "Bu ay"

            elif query.data == 'date_range_manual':
                await self.request_manual_date_input(query)
                return
            else:
                logger.error(f"Unknown date range selection: {query.data}")
                await self.safe_edit_message(query, "<b>❌ Naməlum seçim.</b>", parse_mode='HTML')
                return

            if start_date and end_date:
                logger.info(
                    f"Calculated date range: {start_date} to {end_date}")
                await self.show_date_range_report(query, start_date, end_date, range_name)
            else:
                logger.error("Failed to calculate date range")
                await self.safe_edit_message(query, "<b>❌ Tarix hesablamasında xəta baş verdi.</b>", parse_mode='HTML')

        except Exception as e:
            logger.error(f"Error handling date range selection: {e}")
            await self.safe_edit_message(query, "<b>❌ Tarix hesablamasında xəta baş verdi.</b>", parse_mode='HTML')

    async def show_date_range_report(self, query, start_date, end_date, range_name):
        """Show report for specified date range"""
        try:
            # Format dates for API call
            start_datetime = f"{start_date.isoformat()}T00:00:00"
            end_datetime = f"{end_date.isoformat()}T23:59:59"

            # Call API with date range
            response = requests.get(
                f"{self.base_url}/orders/active-orders/?start_date={start_datetime}&end_date={end_datetime}"
            )

            if response.status_code == 200:
                data = response.json()

                message = f"""<b>📆 {range_name.upper()} HESABATI</b>
📅 {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}

<pre>
┌─────────────────────────────────┐
│         ÖDƏNİŞ STATİSTİKASI     │
├─────────────────────────────────┤
│ 💵 Nağd        │ {data['cash_total']:>8.2f} AZN │
│ 💳 Kart        │ {data['card_total']:>8.2f} AZN │
│ 🔄 Digər       │ {data['other_total']:>8.2f} AZN │
│ ❌ Ödənilməmiş │ {data['unpaid_total']:>8.2f} AZN │
├─────────────────────────────────┤
│         ÜMUMİ MƏBLƏĞ            │
├─────────────────────────────────┤
│ ✅ Ödənilmiş   │ {data['paid_total']:>8.2f} AZN │
│ 📊 Toplam      │ {(data['paid_total'] + data['unpaid_total']):>8.2f} AZN │
└─────────────────────────────────┘
</pre>

🕒 <i>Yenilənmə: {self.get_current_time()}</i>"""

                keyboard = [
                    [InlineKeyboardButton(
                        "🔄 Hesabatı Yenilə", callback_data=query.data)],
                    [InlineKeyboardButton(
                        "📆 Başqa Dövrü", callback_data='date_range_menu')],
                    [InlineKeyboardButton(
                        "🏠 Ana Menyu", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await self.safe_edit_message(query, message, reply_markup, parse_mode='HTML')
            else:
                await self.safe_edit_message(query, "<b>❌ Məlumat alınarkən xəta baş verdi.</b>", parse_mode='HTML')

        except Exception as e:
            logger.error(f"Error fetching date range report: {e}")
            await self.safe_edit_message(query, "<b>❌ Serverlə əlaqə yaradılmadı.</b>", parse_mode='HTML')

    async def request_manual_date_input(self, query):
        """Request manual date input from user"""
        text = """<b>📝 TARİX DAXİL EDİN</b>

<b>🔹 DƏSTƏKLƏNƏN FORMATLAR:</b>
<code>📅 ISO Format:     2025-09-10
🗓️ Avropa Format:   10.09.2025
📋 Slash Format:    10/09/2025
📊 Dash Format:     10-09-2025</code>

<b>🔹 BİR TARİX ÜÇÜN MİSALLAR:</b>
• <code>2025-09-10</code>
• <code>10.09.2025</code>
• <code>10/09/2025</code>

<b>🔹 TARİX ARALIĞI ÜÇÜN MİSALLAR:</b>
• <code>2025-09-01 2025-09-10</code>
• <code>01.09.2025 10.09.2025</code>
• <code>01/09/2025 10/09/2025</code>

<i>📝 İndi tarixi yazın və göndərin...</i>"""

        keyboard = [
            [InlineKeyboardButton("⬅️ Geri", callback_data='date_range_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.safe_edit_message(query, text, reply_markup, parse_mode='HTML')

        # Note: We'll use a simpler approach - just wait for the next text message
        # The user state management is handled in handle_text_input

    async def request_daily_custom_date_input(self, query):
        """Request manual date input from user for daily reports"""
        text = """<b>📝 TARİX DAXİL EDİN</b>

<b>🔹 DƏSTƏKLƏNƏN FORMATLAR:</b>
<code>📅 ISO Format:     2025-09-10
🗓️ Avropa Format:   10.09.2025
📋 Slash Format:    10/09/2025
📊 Dash Format:     10-09-2025</code>

<b>🔹 BİR TARİX ÜÇÜN MİSALLAR:</b>
• <code>2025-09-10</code>
• <code>10.09.2025</code>
• <code>10/09/2025</code>

<i>📝 İndi tarixi yazın və göndərin...</i>"""

        keyboard = [
            [InlineKeyboardButton("⬅️ Geri", callback_data='daily_report')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.safe_edit_message(query, text, reply_markup, parse_mode='HTML')

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input from users"""
        user_id = update.effective_user.id
        text = update.message.text.strip()

        logger.info(f"🔍 Received text input from user {user_id}: '{text}'")

        # Check if user is in continuous AI analyze mode
        if AIAnalyzeCommand.is_ai_analyze_active(context):
            await AIAnalyzeCommand.handle_user_question(update, context)
        # Try to parse as date input first
        elif self.looks_like_date_input(text):
            await self.process_manual_date_input(update, text)
        else:
            # Default response with back button
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🤖 AI Analiz", callback_data='new_ai_analyze')],
                [InlineKeyboardButton(
                    "📊 Hesabatlar", callback_data='main_menu')]
            ])
            await update.message.reply_text(
                f"🤖 Mətn alındı: <code>{text}</code>\n\n"
                "Sifariş hesabatları üçün <b>📊 Hesabatlar</b> düyməsini basın.\n\n"
                "AI analiz üçün <b>🤖 AI Analiz</b> düyməsini basın.",
                reply_markup=keyboard,
                parse_mode='HTML'
            )

    def looks_like_date_input(self, text):
        """Check if text looks like a date input"""
        parts = text.split()
        if len(parts) == 0 or len(parts) > 2:
            return False

        # Check if all parts look like dates and use the same format
        detected_format = None
        for part in parts:
            part_format = self.detect_date_format(part)
            if part_format is None:
                return False  # Invalid date format

            if detected_format is None:
                detected_format = part_format
            elif detected_format != part_format:
                return False  # Mixed formats not allowed

        return True

    def detect_date_format(self, date_str):
        """Detect the format of a date string"""
        formats = [
            ('%Y-%m-%d', 'iso'),        # 2025-01-15
            ('%d.%m.%Y', 'european'),   # 15.01.2025
            ('%d/%m/%Y', 'slash'),      # 15/01/2025
            ('%d-%m-%Y', 'dash'),       # 15-01-2025
        ]

        for fmt, format_name in formats:
            try:
                datetime.strptime(date_str, fmt)
                return format_name
            except ValueError:
                continue

        return None

    def is_valid_date_format(self, date_str):
        """Check if a string is a valid date in any supported format"""
        return self.detect_date_format(date_str) is not None

    def parse_date_string(self, date_str):
        """Parse a date string in any supported format to a date object"""
        formats = [
            '%Y-%m-%d',     # 2025-01-15
            '%d.%m.%Y',     # 15.01.2025
            '%d/%m/%Y',     # 15/01/2025
            '%d-%m-%Y',     # 15-01-2025
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Invalid date format: {date_str}")

    async def process_manual_date_input(self, update, text):
        """Process manually entered dates"""
        try:
            logger.info(f"Processing manual date input: '{text}'")
            parts = text.split()

            if len(parts) == 1:
                # Single date
                try:
                    input_date = self.parse_date_string(parts[0])
                    logger.info(f"Parsed single date: {input_date}")
                    await self.show_single_date_report_with_context(update, input_date, 'daily_report')
                except ValueError as e:
                    logger.error(f"Invalid single date format: {e}")
                    await update.message.reply_text(
                        "<b>❌ XƏTA BAŞ VERDİ</b>\n\n"
                        "Yanlış tarix formatı!\n\n"
                        "<b>🔹 DƏSTƏKLƏNƏN FORMATLAR:</b>\n"
                        "<code>📅 2025-01-15\n"
                        "🗓️ 15.01.2025\n"
                        "📋 15/01/2025\n"
                        "📊 15-01-2025</code>\n\n"
                        "<i>💡 Yenidən cəhd edin...</i>",
                        parse_mode='HTML'
                    )

            elif len(parts) == 2:
                # Date range
                try:
                    start_date = self.parse_date_string(parts[0])
                    end_date = self.parse_date_string(parts[1])

                    logger.info(
                        f"Parsed date range: {start_date} to {end_date}")

                    if start_date > end_date:
                        await update.message.reply_text("<b>❌ Başlanğıc tarixi bitiş tarixindən böyük ola bilməz!</b>", parse_mode='HTML')
                        return

                    await self.show_manual_date_range_report_with_context(update, start_date, end_date, 'date_range_menu')
                except ValueError as e:
                    logger.error(f"Invalid date range format: {e}")
                    await update.message.reply_text(
                        "<b>❌ XƏTA BAŞ VERDİ</b>\n\n"
                        "Yanlış tarix formatı!\n\n"
                        "<b>🔹 TARİX ARALIĞI FORMATLAR:</b>\n"
                        "<code>📅 2025-01-15 2025-01-20\n"
                        "🗓️ 15.01.2025 20.01.2025\n"
                        "📋 15/01/2025 20/01/2025\n"
                        "📊 15-01-2025 20-01-2025</code>\n\n"
                        "<i>💡 Yenidən cəhd edin...</i>",
                        parse_mode='HTML'
                    )
            else:
                logger.warning(f"Wrong number of date parts: {len(parts)}")
                await update.message.reply_text("<b>❌ Yanlış format!</b> Bir tarix və ya iki tarix daxil edin.", parse_mode='HTML')

        except Exception as e:
            logger.error(f"Error processing manual date input: {e}")
            await update.message.reply_text("<b>❌ Tarix işləməsində xəta baş verdi.</b>", parse_mode='HTML')

    async def show_single_date_report_with_context(self, update, target_date, context='daily_report'):
        """Show report for a single date with proper navigation context"""
        try:
            logger.info(
                f"Fetching single date report for: {target_date} with context: {context}")

            # Call API for specific date
            api_url = f"{self.base_url}/orders/active-orders/?date={target_date.isoformat()}"
            logger.info(f"API call: {api_url}")

            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"API response successful: {data}")

                message = f"""<b>📊 {target_date.strftime('%d.%m.%Y')} HESABATI</b>

<pre>
┌─────────────────────────────────┐
│         ÖDƏNİŞ STATİSTİKASI     │
├─────────────────────────────────┤
│ 💵 Nağd        │ {data['cash_total']:>8.2f} AZN │
│ 💳 Kart        │ {data['card_total']:>8.2f} AZN │
│ 🔄 Digər       │ {data['other_total']:>8.2f} AZN │
│ ❌ Ödənilməmiş │ {data['unpaid_total']:>8.2f} AZN │
├─────────────────────────────────┤
│         ÜMUMİ MƏBLƏĞ            │
├─────────────────────────────────┤
│ ✅ Ödənilmiş   │ {data['paid_total']:>8.2f} AZN │
│ 📊 Toplam      │ {(data['paid_total'] + data['unpaid_total']):>8.2f} AZN │
└─────────────────────────────────┘
</pre>

🕒 <i>Yenilənmə: {self.get_current_time()}</i>"""

                # Create navigation buttons based on context
                keyboard = [
                    [InlineKeyboardButton(
                        "🔄 Hesabatı Yenilə", callback_data=f'refresh_single_date_{target_date.isoformat()}_{context}')],
                    [InlineKeyboardButton(
                        "⬅️ Geri Qayıt", callback_data=context)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await self.safe_reply_text(update, message.strip(), reply_markup=reply_markup, parse_mode='HTML')
            else:
                logger.error(
                    f"API error: {response.status_code} - {response.text}")
                await update.message.reply_text("<b>❌ Məlumat alınarkən xəta baş verdi.</b>", parse_mode='HTML')

        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error fetching single date report: {e}")
            await update.message.reply_text("<b>❌ Serverlə əlaqə yaradılmadı.</b>", parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error fetching single date report: {e}")
            await update.message.reply_text("<b>❌ Hesabat hazırlanarkən xəta baş verdi.</b>", parse_mode='HTML')

    async def show_single_date_report(self, update, target_date):
        """Show report for a single date (legacy method for compatibility)"""
        await self.show_single_date_report_with_context(update, target_date, 'main_menu')

    async def show_manual_date_range_report_with_context(self, update, start_date, end_date, context='date_range_menu'):
        """Show report for manually entered date range with proper navigation context"""
        try:
            logger.info(
                f"Fetching manual date range report: {start_date} to {end_date} with context: {context}")

            # Format dates for API call
            start_datetime = f"{start_date.isoformat()}T00:00:00"
            end_datetime = f"{end_date.isoformat()}T23:59:59"

            api_url = f"{self.base_url}/orders/active-orders/?start_date={start_datetime}&end_date={end_datetime}"
            logger.info(f"API call: {api_url}")

            # Call API with date range
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"API response successful: {data}")

                message = f"""<b>📆 SEÇİLMİŞ DÖVRÜN HESABATI</b>
📅 {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}

<pre>
┌─────────────────────────────────┐
│         ÖDƏNİŞ STATİSTİKASI     │
├─────────────────────────────────┤
│ 💵 Nağd        │ {data['cash_total']:>8.2f} AZN │
│ 💳 Kart        │ {data['card_total']:>8.2f} AZN │
│ 🔄 Digər       │ {data['other_total']:>8.2f} AZN │
│ ❌ Ödənilməmiş │ {data['unpaid_total']:>8.2f} AZN │
├─────────────────────────────────┤
│         ÜMUMİ MƏBLƏĞ            │
├─────────────────────────────────┤
│ ✅ Ödənilmiş   │ {data['paid_total']:>8.2f} AZN │
│ 📊 Toplam      │ {(data['paid_total'] + data['unpaid_total']):>8.2f} AZN │
└─────────────────────────────────┘
</pre>

🕒 <i>Yenilənmə: {self.get_current_time()}</i>"""

                # Create navigation buttons based on context
                keyboard = [
                    [InlineKeyboardButton(
                        "🔄 Hesabatı Yenilə", callback_data=f'refresh_date_range_{start_date.isoformat()}_{end_date.isoformat()}_{context}')],
                    [InlineKeyboardButton(
                        "⬅️ Geri Qayıt", callback_data=context)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await self.safe_reply_text(update, message.strip(), reply_markup=reply_markup, parse_mode='HTML')
            else:
                logger.error(
                    f"API error: {response.status_code} - {response.text}")
                await update.message.reply_text("<b>❌ Məlumat alınarkən xəta baş verdi.</b>", parse_mode='HTML')

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Connection error fetching manual date range report: {e}")
            await update.message.reply_text("<b>❌ Serverlə əlaqə yaradılmadı.</b>", parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error fetching manual date range report: {e}")
            await update.message.reply_text("<b>❌ Hesabat hazırlanarkən xəta baş verdi.</b>", parse_mode='HTML')

    async def show_manual_date_range_report(self, update, start_date, end_date):
        """Show report for manually entered date range (legacy method for compatibility)"""
        await self.show_manual_date_range_report_with_context(update, start_date, end_date, 'date_range_menu')

    async def handle_refresh_single_date(self, query):
        """Handle refresh button for single date reports"""
        try:
            # Parse callback data: refresh_single_date_2025-01-15_daily_report
            parts = query.data.split('_')
            date_str = parts[3]  # 2025-01-15
            context = '_'.join(parts[4:])  # daily_report or date_range_menu

            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # Create a mock update object for the refresh
            class MockUpdate:
                def __init__(self, query):
                    self.message = query.message

            mock_update = MockUpdate(query)
            await self.show_single_date_report_with_context(mock_update, target_date, context)
        except Exception as e:
            logger.error(f"Error refreshing single date report: {e}")
            await self.safe_edit_message(query, "<b>❌ Yenilənmə zamanı xəta baş verdi.</b>", parse_mode='HTML')

    async def handle_refresh_date_range(self, query):
        """Handle refresh button for date range reports"""
        try:
            # Parse callback data: refresh_date_range_2025-01-01_2025-01-31_date_range_menu
            parts = query.data.split('_')
            start_date_str = parts[3]  # 2025-01-01
            end_date_str = parts[4]    # 2025-01-31
            context = '_'.join(parts[5:])  # date_range_menu

            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            # Create a mock update object for the refresh
            class MockUpdate:
                def __init__(self, query):
                    self.message = query.message

            mock_update = MockUpdate(query)
            await self.show_manual_date_range_report_with_context(mock_update, start_date, end_date, context)
        except Exception as e:
            logger.error(f"Error refreshing date range report: {e}")
            await self.safe_edit_message(query, "<b>❌ Yenilənmə zamanı xəta baş verdi.</b>", parse_mode='HTML')

    def get_current_time(self):
        """Get current time formatted"""
        return datetime.now().strftime("%H:%M:%S")

    async def safe_edit_message(self, query, text, reply_markup=None, parse_mode=None):
        """Safely edit message, handling duplicate content errors"""
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            if "Message is not modified" in str(e):
                # Message content is the same, just acknowledge the callback
                logger.info("Message content unchanged, skipping edit")
                pass
            else:
                # Re-raise other errors
                logger.error(f"Error editing message: {e}")
                raise

    async def safe_reply_text(self, update, text, reply_markup=None, parse_mode=None):
        """Safely send reply text message"""
        try:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            raise

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
