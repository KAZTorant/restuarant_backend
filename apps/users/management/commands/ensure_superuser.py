import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a default superuser if it does not exist yet.'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('SUPERUSER_USERNAME', 'admin')
        password = os.environ.get('SUPERUSER_PASSWORD', 'admin123')
        email = os.environ.get('SUPERUSER_EMAIL', 'admin@example.com')

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser "{username}" already exists, skipping.')
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            type='admin',
        )
        self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created.'))
