import sys

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.orders.telegram_bot.bot import RestaurantBot


class Command(BaseCommand):
    help = 'Run the Telegram bot for restaurant orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--token',
            type=str,
            help='Telegram bot token (overrides settings)',
        )

    def handle(self, *args, **options):
        # Get token from command line or settings
        token = options.get('token') or getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        
        if not token:
            self.stdout.write(
                self.style.ERROR(
                    'Please provide a bot token via --token argument or '
                    'set TELEGRAM_BOT_TOKEN in your Django settings'
                )
            )
            return

        self.stdout.write(self.style.SUCCESS('Starting Restaurant Telegram Bot...'))
        self.stdout.write(f'Base URL: {getattr(settings, "BASE_URL", "http://127.0.0.1:8000")}')
        
        try:
            # Create and run the bot
            bot = RestaurantBot(token)
            
            # Run the bot synchronously (no asyncio.run needed)
            bot.run()
            
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('\nBot stopped by user.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error running bot: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())