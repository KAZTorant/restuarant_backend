from django.core.management.base import BaseCommand

from apps.tenants.import_export import export_to_json_file
from apps.tenants.models import Restaurant


class Command(BaseCommand):
    help = 'Restoran məlumatlarını JSON fayla export edir (local bazadan köçürmə üçün).'

    def add_arguments(self, parser):
        parser.add_argument(
            '-o', '--output',
            default='restaurant_export.json',
            help='Çıxış faylının yolu',
        )
        parser.add_argument(
            '--slug',
            default=None,
            help='Mövcud restoran slug-u (boşdursa bütün legacy məlumat export olunur)',
        )

    def handle(self, *args, **options):
        restaurant = None
        if options['slug']:
            restaurant = Restaurant.objects.filter(slug=options['slug']).first()
            if not restaurant:
                self.stderr.write(self.style.ERROR(
                    f'Restoran tapılmadı: {options["slug"]}'
                ))
                return

        path = options['output']
        payload = export_to_json_file(path, restaurant=restaurant)
        model_count = sum(len(v) for v in payload['models'].values())
        self.stdout.write(self.style.SUCCESS(
            f'{model_count} qeyd export edildi → {path}'
        ))
