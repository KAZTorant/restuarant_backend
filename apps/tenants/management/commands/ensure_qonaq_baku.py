import gzip
import json
import os

from django.core.management.base import BaseCommand
from django.db import connection

from apps.meals.models import Meal
from apps.tenants.import_export import import_restaurant_data
from apps.tenants.models import Restaurant


class Command(BaseCommand):
    help = 'Qonaq-Baku restoranını və dump məlumatlarını Railway deploy zamanı yükləyir.'

    RESTAURANT_NAME = 'Qonaq-Baku'
    RESTAURANT_SLUG = 'qonaq-baku'
    DEFAULT_DATA_PATH = 'data/qonaq_baku.json.gz'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Mövcud məlumat olsa belə yenidən import et',
        )
        parser.add_argument(
            '--data-path',
            default=None,
            help='Import JSON.gz faylının yolu',
        )

    def handle(self, *args, **options):
        data_path = options['data_path'] or os.environ.get(
            'QONAQ_BAKU_DATA_PATH',
            self.DEFAULT_DATA_PATH,
        )

        restaurant = Restaurant.objects.filter(slug=self.RESTAURANT_SLUG).first()
        if restaurant and not options['force']:
            has_meals = Meal.objects.filter(
                category__group__restaurant=restaurant,
            ).exists()
            if has_meals:
                self.stdout.write(self.style.WARNING(
                    f'{self.RESTAURANT_NAME} artıq məlumatla mövcuddur, import atlanır.'
                ))
                return

        if not os.path.isfile(data_path):
            self.stdout.write(self.style.WARNING(
                f'Import faylı tapılmadı ({data_path}), Qonaq-Baku seed atlanır.'
            ))
            return

        restaurant, created = Restaurant.objects.get_or_create(
            slug=self.RESTAURANT_SLUG,
            defaults={
                'name': self.RESTAURANT_NAME,
                'is_active': True,
            },
        )
        if not created and restaurant.name != self.RESTAURANT_NAME:
            restaurant.name = self.RESTAURANT_NAME
            restaurant.save(update_fields=['name'])

        with gzip.open(data_path, 'rt', encoding='utf-8') as handle:
            payload = json.load(handle)

        if options['force'] and not created:
            self._clear_restaurant_data(restaurant)

        id_map = import_restaurant_data(restaurant, payload)
        self._reset_sequences()

        model_count = sum(len(v) for v in payload.get('models', {}).values())
        self.stdout.write(self.style.SUCCESS(
            f'{self.RESTAURANT_NAME} import tamamlandı: {model_count} qeyd, '
            f'{len(id_map)} obyekt xəritələndi.'
        ))

    def _clear_restaurant_data(self, restaurant):
        """Force import üçün restoran tenant məlumatını silir."""
        from django.apps import apps

        tenant_models = [
            ('orders', 'OrderItemDeletionLog'),
            ('printers', 'Receipt'),
            ('inventory_connector', 'MealInventoryMapping'),
            ('inventory_connector', 'MealInventoryConnector'),
            ('payments', 'PaymentMethod'),
            ('payments', 'Payment'),
            ('orders', 'OrderItem'),
            ('orders', 'Order'),
            ('orders', 'Statistics'),
            ('orders', 'Summary'),
            ('orders', 'Report'),
            ('orders', 'WorkPeriodConfig'),
            ('payments', 'PaymentCalculation'),
            ('finance', 'Income'),
            ('finance', 'Expense'),
            ('users', 'ShiftHandover'),
            ('users', 'WhatsAppConfig'),
            ('tables', 'Table'),
            ('tables', 'Room'),
            ('meals', 'Meal'),
            ('meals', 'MealCategory'),
            ('meals', 'MealGroup'),
            ('printers', 'PreparationPlace'),
            ('printers', 'Printer'),
            ('printers', 'PrintGatewayLocation'),
            ('inventory', 'InventoryRecord'),
            ('inventory', 'InventoryItem'),
            ('inventory', 'Supplier'),
            ('inventory', 'Category'),
            ('users', 'User'),
        ]
        for app_label, model_name in reversed(tenant_models):
            model = apps.get_model(app_label, model_name)
            if not hasattr(model, 'restaurant_id'):
                continue
            if not self._model_has_restaurant_column(model):
                continue
            if model_name == 'User':
                model.objects.filter(restaurant=restaurant).delete()
            else:
                model.objects.filter(restaurant=restaurant).delete()

    def _model_has_restaurant_column(self, model):
        from django.db import connection

        if connection.vendor != 'postgresql':
            return hasattr(model, 'restaurant_id')
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_name = %s AND column_name = 'restaurant_id'
                """,
                [model._meta.db_table],
            )
            return cursor.fetchone() is not None

    def _reset_sequences(self):
        """Importdan sonra PostgreSQL sequence-lərini yeniləyir."""
        if connection.vendor != 'postgresql':
            return
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'S' AND n.nspname = 'public'
                """
            )
            for (seq_name,) in cursor.fetchall():
                table_name = seq_name.rsplit('_', 1)[0]
                if not seq_name.endswith('_id_seq'):
                    continue
                cursor.execute(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = %s
                    """,
                    [table_name],
                )
                if not cursor.fetchone():
                    continue
                cursor.execute(
                    f"""
                    SELECT setval(%s, COALESCE((SELECT MAX(id) FROM {table_name}), 1))
                    """,
                    [seq_name],
                )
