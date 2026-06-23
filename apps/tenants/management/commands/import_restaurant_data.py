from django.core.management.base import BaseCommand, CommandError

from apps.tenants.import_export import import_from_json_file
from apps.tenants.models import Restaurant


class Command(BaseCommand):
    help = 'JSON export faylını restorana import edir.'

    def add_arguments(self, parser):
        parser.add_argument('slug', help='Hədəf restoran slug-u')
        parser.add_argument('file', help='Import JSON faylının yolu')

    def handle(self, *args, **options):
        restaurant = Restaurant.objects.filter(slug=options['slug']).first()
        if not restaurant:
            raise CommandError(f'Restoran tapılmadı: {options["slug"]}')

        id_map = import_from_json_file(restaurant, options['file'])
        self.stdout.write(self.style.SUCCESS(
            f'Import tamamlandı: {restaurant.name} ({len(id_map)} obyekt)'
        ))
