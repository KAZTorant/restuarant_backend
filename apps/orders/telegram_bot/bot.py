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
            CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_text_input))

        logger.info("Handlers set up successfully")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when /start command is issued"""
        logger.info(
            f"Start command received from user: {update.effective_user.id}")
        welcome_text = """
🍽️ Restoran Bot-a xoş gəldiniz!

Bu bot vasitəsilə restoranın sifariş hesabatlarını izləyə bilərsiniz.

Əmrlər:
/orders - Sifariş hesabatları
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
        logger.info(
            f"Help command received from user: {update.effective_user.id}")
        help_text = """
🆘 Kömək

Mövcud əmrlər:
/start - Başlanğıc mesajı
/orders - Sifariş hesabatlarını göstər
/help - Bu kömək mesajı

Düymələr vasitəsilə naviqasiya edə bilərsiniz.
        """
        try:
            await update.message.reply_text(help_text)
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

        text = """
📋 Sifariş Hesabatları

Seçimlər:
📈 Günün Hesabatı
📆 Tarix/Vaxt Aralığı - Seçdiyiniz dövrün sifarişləri

İstədiyiniz hesabat növünü seçin:
        """

        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

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
            await self.orders_menu(update, context)
        elif query.data.startswith('date_range_'):
            await self.handle_date_range_selection(query)

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

                message = f"""
📅 Bugünkü Hesabat ({today})

💰 Ödəniş Statistikası:
├ 💵 Nağd: {data['cash_total']:.2f} AZN
├ 💳 Kart: {data['card_total']:.2f} AZN  
├ 🔄 Digər: {data['other_total']:.2f} AZN
└ ❌ Ödənilməmiş: {data['unpaid_total']:.2f} AZN

📊 Ümumi:
├ Ödənilmiş: {data['paid_total']:.2f} AZN
└ Toplam: {(data['paid_total'] + data['unpaid_total']):.2f} AZN

🔄 Yenilənmə: {self.get_current_time()}
                """

                keyboard = [
                    [InlineKeyboardButton(
                        "🔄 Yenilə", callback_data='today_report')],
                    [InlineKeyboardButton(
                        "⬅️ Geri", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ Məlumat alınarkən xəta baş verdi.")

        except Exception as e:
            logger.error(f"Error fetching today's report: {e}")
            await query.edit_message_text("❌ Serverlə əlaqə yaradılmadı.")

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

            # Add back button
            keyboard.append([InlineKeyboardButton(
                "⬅️ Geri", callback_data='main_menu')])

            reply_markup = InlineKeyboardMarkup(keyboard)

            text = """
📈 Günün Hesabatı

Son 7 iş dövrünün hesabatlarını görmək üçün tarixi seçin:
(Tarixlər iş dövrünün başlama vaxtına görədir)
            """

            await query.edit_message_text(text, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Error showing daily report menu: {e}")
            await query.edit_message_text("❌ Menyu yüklənərkən xəta baş verdi.")

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
                    message = f"""
📈 Günün Hesabatı ({date_str})

❌ {data.get('error', 'Xəta baş verdi')}
                    """
                    keyboard = [
                        [InlineKeyboardButton(
                            "⬅️ Geri", callback_data='daily_report')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(message, reply_markup=reply_markup)
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

                message = f"""
📈 Günün Hesabatı
{display_date} {time_range}

💰 Ödəniş Statistikası:
├ 💵 Nağd: {data['cash_total']:.2f} AZN
├ 💳 Kart: {data['card_total']:.2f} AZN  
├ 🔄 Digər: {data['other_total']:.2f} AZN
└ ❌ Ödənilməmiş: {data['unpaid_total']:.2f} AZN

📊 Ümumi:
├ Ödənilmiş: {data['paid_total']:.2f} AZN
└ Toplam: {(data['paid_total'] + data['unpaid_total']):.2f} AZN

📋 Dövrü: {data['period_name']}
🔄 Yenilənmə: {self.get_current_time()}
                """

                keyboard = [
                    [InlineKeyboardButton(
                        "🔄 Yenilə", callback_data=f'period_report_{date_str}')],
                    [InlineKeyboardButton(
                        "⬅️ Geri", callback_data='daily_report')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ Məlumat alınarkən xəta baş verdi.")

        except Exception as e:
            logger.error(f"Error fetching period report for {date_str}: {e}")
            await query.edit_message_text("❌ Serverlə əlaqə yaradılmadı.")

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

        text = """
📆 Tarix/Vaxt Aralığı Seçin

Hazır seçimlər:
📅 Bu həftə - Bu həftənin sifarişləri
📅 Keçən həftə - Keçən həftənin sifarişləri  
📅 Bu ay - Bu ayın sifarişləri
📝 Əl ilə daxil et - Özünüz tarix seçin

Seçiminizi edin:
        """

        await query.edit_message_text(text, reply_markup=reply_markup)

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
                await query.edit_message_text("❌ Naməlum seçim.")
                return

            if start_date and end_date:
                logger.info(
                    f"Calculated date range: {start_date} to {end_date}")
                await self.show_date_range_report(query, start_date, end_date, range_name)
            else:
                logger.error("Failed to calculate date range")
                await query.edit_message_text("❌ Tarix hesablamasında xəta baş verdi.")

        except Exception as e:
            logger.error(f"Error handling date range selection: {e}")
            await query.edit_message_text("❌ Tarix hesablamasında xəta baş verdi.")

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

                message = f"""
📆 {range_name} Hesabatı
({start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')})

💰 Ödəniş Statistikası:
├ 💵 Nağd: {data['cash_total']:.2f} AZN
├ 💳 Kart: {data['card_total']:.2f} AZN  
├ 🔄 Digər: {data['other_total']:.2f} AZN
└ ❌ Ödənilməmiş: {data['unpaid_total']:.2f} AZN

📊 Ümumi:
├ Ödənilmiş: {data['paid_total']:.2f} AZN
└ Toplam: {(data['paid_total'] + data['unpaid_total']):.2f} AZN

🔄 Yenilənmə: {self.get_current_time()}
                """

                keyboard = [
                    [InlineKeyboardButton(
                        "🔄 Yenilə", callback_data=query.data)],
                    [InlineKeyboardButton(
                        "📆 Başqa dövrü", callback_data='date_range_menu')],
                    [InlineKeyboardButton(
                        "⬅️ Ana menyu", callback_data='main_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(message, reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ Məlumat alınarkən xəta baş verdi.")

        except Exception as e:
            logger.error(f"Error fetching date range report: {e}")
            await query.edit_message_text("❌ Serverlə əlaqə yaradılmadı.")

    async def request_manual_date_input(self, query):
        """Request manual date input from user"""
        text = """
📝 Əl ilə Tarix Daxil Etmə

Zəhmət olmasa tarixi aşağıdakı formatlardan birində daxil edin:

🔹 Dəstəklənən formatlar:
• 2025-09-10 (ISO formatı)
• 10.09.2025 (Avropa formatı) 
• 10/09/2025 (Slash formatı)
• 10-09-2025 (Dash formatı)

🔹 Bir tarix üçün misallar:
• 2025-09-10
• 10.09.2025
• 10/09/2025

🔹 Tarix aralığı üçün misallar:
• 2025-09-01 2025-09-10
• 01.09.2025 10.09.2025
• 01/09/2025 10/09/2025

İndi tarixi yazın və göndərin...
        """

        keyboard = [
            [InlineKeyboardButton("⬅️ Geri", callback_data='date_range_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup)

        # Note: We'll use a simpler approach - just wait for the next text message
        # The user state management is handled in handle_text_input

    async def handle_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text input from users"""
        user_id = update.effective_user.id
        text = update.message.text.strip()

        logger.info(f"🔍 Received text input from user {user_id}: '{text}'")

        # Try to parse as date input first
        if self.looks_like_date_input(text):
            await self.process_manual_date_input(update, text)
        else:
            # Default response for non-date input
            await update.message.reply_text(
                f"🤖 Mətn alındı: {text}\n\nSifariş hesabatları üçün /orders komandası istifadə edin."
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
                    await self.show_single_date_report(update, input_date)
                except ValueError as e:
                    logger.error(f"Invalid single date format: {e}")
                    await update.message.reply_text(
                        "❌ Yanlış tarix formatı!\n\n"
                        "Dəstəklənən formatlar:\n"
                        "• 2025-01-15\n"
                        "• 15.01.2025\n"
                        "• 15/01/2025\n"
                        "• 15-01-2025"
                    )

            elif len(parts) == 2:
                # Date range
                try:
                    start_date = self.parse_date_string(parts[0])
                    end_date = self.parse_date_string(parts[1])

                    logger.info(
                        f"Parsed date range: {start_date} to {end_date}")

                    if start_date > end_date:
                        await update.message.reply_text("❌ Başlanğıc tarixi bitiş tarixindən böyük ola bilməz!")
                        return

                    await self.show_manual_date_range_report(update, start_date, end_date)
                except ValueError as e:
                    logger.error(f"Invalid date range format: {e}")
                    await update.message.reply_text(
                        "❌ Yanlış tarix formatı!\n\n"
                        "Dəstəklənən formatlar:\n"
                        "• 2025-01-15 2025-01-20\n"
                        "• 15.01.2025 20.01.2025\n"
                        "• 15/01/2025 20/01/2025\n"
                        "• 15-01-2025 20-01-2025"
                    )
            else:
                logger.warning(f"Wrong number of date parts: {len(parts)}")
                await update.message.reply_text("❌ Yanlış format! Bir tarix və ya iki tarix daxil edin.")

        except Exception as e:
            logger.error(f"Error processing manual date input: {e}")
            await update.message.reply_text("❌ Tarix işləməsində xəta baş verdi.")

    async def show_single_date_report(self, update, target_date):
        """Show report for a single date"""
        try:
            logger.info(f"Fetching single date report for: {target_date}")

            # Call API for specific date
            api_url = f"{self.base_url}/orders/active-orders/?date={target_date.isoformat()}"
            logger.info(f"API call: {api_url}")

            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"API response successful: {data}")

                message = f"""
📅 {target_date.strftime('%d.%m.%Y')} Hesabatı

💰 Ödəniş Statistikası:
├ 💵 Nağd: {data['cash_total']:.2f} AZN
├ 💳 Kart: {data['card_total']:.2f} AZN  
├ 🔄 Digər: {data['other_total']:.2f} AZN
└ ❌ Ödənilməmiş: {data['unpaid_total']:.2f} AZN

📊 Ümumi:
├ Ödənilmiş: {data['paid_total']:.2f} AZN
└ Toplam: {(data['paid_total'] + data['unpaid_total']):.2f} AZN

🔄 Yenilənmə: {self.get_current_time()}
                """

                await update.message.reply_text(message.strip())
            else:
                logger.error(
                    f"API error: {response.status_code} - {response.text}")
                await update.message.reply_text("❌ Məlumat alınarkən xəta baş verdi.")

        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error fetching single date report: {e}")
            await update.message.reply_text("❌ Serverlə əlaqə yaradılmadı.")
        except Exception as e:
            logger.error(f"Error fetching single date report: {e}")
            await update.message.reply_text("❌ Hesabat hazırlanarkən xəta baş verdi.")

    async def show_manual_date_range_report(self, update, start_date, end_date):
        """Show report for manually entered date range"""
        try:
            logger.info(
                f"Fetching manual date range report: {start_date} to {end_date}")

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

                message = f"""
📆 Seçilmiş Dövrün Hesabatı
({start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')})

💰 Ödəniş Statistikası:
├ 💵 Nağd: {data['cash_total']:.2f} AZN
├ 💳 Kart: {data['card_total']:.2f} AZN  
├ 🔄 Digər: {data['other_total']:.2f} AZN
└ ❌ Ödənilməmiş: {data['unpaid_total']:.2f} AZN

📊 Ümumi:
├ Ödənilmiş: {data['paid_total']:.2f} AZN
└ Toplam: {(data['paid_total'] + data['unpaid_total']):.2f} AZN

🔄 Yenilənmə: {self.get_current_time()}
                """

                await update.message.reply_text(message.strip())
            else:
                logger.error(
                    f"API error: {response.status_code} - {response.text}")
                await update.message.reply_text("❌ Məlumat alınarkən xəta baş verdi.")

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Connection error fetching manual date range report: {e}")
            await update.message.reply_text("❌ Serverlə əlaqə yaradılmadı.")
        except Exception as e:
            logger.error(f"Error fetching manual date range report: {e}")
            await update.message.reply_text("❌ Hesabat hazırlanarkən xəta baş verdi.")

    def get_current_time(self):
        """Get current time formatted"""
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
