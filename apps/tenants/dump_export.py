"""Legacy PostgreSQL bazasından (dump restore) tenant JSON payload export edir."""

from datetime import date, datetime, time
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from apps.tenants.import_export import M2M_FIELDS, _model_label

SKIP_SOURCE_TABLES = {
    'django_migrations',
    'django_session',
    'django_admin_log',
    'django_content_type',
    'auth_group',
    'auth_group_permissions',
    'auth_permission',
    'users_user_groups',
    'users_user_user_permissions',
}

# (app_label, model_name) -> source table name
SOURCE_TABLES = [
    ('users', 'User', 'users_user'),
    ('printers', 'Printer', 'printers_printer'),
    ('printers', 'PreparationPlace', 'printers_preparationplace'),
    ('meals', 'MealGroup', 'meals_mealgroup'),
    ('meals', 'MealCategory', 'meals_mealcategory'),
    ('meals', 'Meal', 'meals_meal'),
    ('tables', 'Room', 'tables_room'),
    ('tables', 'Table', 'tables_table'),
    ('orders', 'WorkPeriodConfig', 'orders_workperiodconfig'),
    ('orders', 'Statistics', 'orders_statistics'),
    ('orders', 'Order', 'orders_order'),
    ('orders', 'OrderItem', 'orders_orderitem'),
    ('payments', 'Payment', 'payments_payment'),
    ('payments', 'PaymentMethod', 'payments_paymentmethod'),
    ('finance', 'Income', 'finance_income'),
    ('finance', 'Expense', 'finance_expense'),
    ('users', 'ShiftHandover', 'users_shifthandover'),
    ('orders', 'Summary', 'orders_summary'),
    ('orders', 'Report', 'orders_report'),
    ('payments', 'PaymentCalculation', 'payments_paymentcalculation'),
    ('inventory_connector', 'MealInventoryConnector', 'inventory_connector_mealinventoryconnector'),
    ('inventory_connector', 'MealInventoryMapping', 'inventory_connector_mealinventorymapping'),
    ('printers', 'Receipt', 'printers_receipt'),
    ('orders', 'OrderItemDeletionLog', 'orders_orderitemdeletionlog'),
    ('inventory', 'Category', 'inventory_category'),
    ('inventory', 'Supplier', 'inventory_supplier'),
    ('inventory', 'InventoryItem', 'inventory_inventoryitem'),
    ('inventory', 'InventoryRecord', 'inventory_inventoryrecord'),
]

M2M_SOURCE_TABLES = {
    'meals.Meal': ('meals_meal_preparation_places', 'meal_id', 'preparationplace_id', 'preparation_places'),
    'orders.Statistics': ('orders_statistics_orders', 'statistics_id', 'order_id', 'orders'),
    'orders.Summary': ('orders_summary_statistics', 'summary_id', 'statistics_id', 'statistics'),
    'orders.Report': ('orders_report_orders', 'report_id', 'order_id', 'orders'),
    'payments.Payment': ('payments_payment_orders', 'payment_id', 'order_id', 'orders'),
    'payments.PaymentCalculation': (
        'payments_paymentcalculation_payments',
        'paymentcalculation_id',
        'payment_id',
        'payments',
    ),
    'printers.Receipt': ('printers_receipt_orders', 'receipt_id', 'order_id', 'orders'),
}

USER_SKIP_FIELDS = {'id', 'last_login', 'date_joined', 'restaurant_id'}
SKIP_FIELDS = {'id', 'restaurant_id'}


def _serialize_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _table_exists(cursor, table_name):
    cursor.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        """,
        [table_name],
    )
    return cursor.fetchone() is not None


def _table_columns(cursor, table_name):
    cursor.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        [table_name],
    )
    return {row['column_name'] for row in cursor.fetchall()}


def export_from_database(database_url, include_history=False):
    """Legacy bazadan import/export formatında payload qaytarır."""
    from django.apps import apps

    payload = {
        'version': 1,
        'exported_at': datetime.now().isoformat(),
        'restaurant_slug': None,
        'source': 'postgresql_dump',
        'models': {},
        'm2m': {},
    }

    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for app_label, model_name, table_name in SOURCE_TABLES:
                if not _table_exists(cursor, table_name):
                    continue

                model = apps.get_model(app_label, model_name)
                label = _model_label(model)
                source_cols = _table_columns(cursor, table_name)

                skip = USER_SKIP_FIELDS if model._meta.model_name == 'user' else SKIP_FIELDS
                field_map = {}
                for field in model._meta.fields:
                    if field.name in skip or field.name == 'id':
                        continue
                    if field.is_relation and not field.many_to_many:
                        col = field.column
                        if col in source_cols:
                            field_map[field.name] = col
                    elif field.column in source_cols:
                        field_map[field.name] = field.column

                where = ''
                params = []
                if table_name == 'users_user':
                    where = 'WHERE is_superuser = FALSE'

                cursor.execute(f'SELECT * FROM {table_name} {where} ORDER BY id', params)
                records = []
                for row in cursor.fetchall():
                    data = {'_pk': row['id']}
                    for field_name, col in field_map.items():
                        data[field_name] = _serialize_value(row.get(col))
                    records.append(data)
                payload['models'][label] = records

            for m2m_key, (table_name, obj_col, related_col, field_name) in M2M_SOURCE_TABLES.items():
                if m2m_key not in M2M_FIELDS:
                    continue
                if not _table_exists(cursor, table_name):
                    continue

                cursor.execute(
                    f'SELECT {obj_col} AS obj_pk, {related_col} AS related_pk FROM {table_name} ORDER BY id'
                )
                grouped = {}
                for row in cursor.fetchall():
                    grouped.setdefault(row['obj_pk'], []).append(row['related_pk'])

                if not grouped:
                    continue

                app_label, model_name = m2m_key.split('.')
                label = _model_label(apps.get_model(app_label, model_name))
                payload['m2m'][label] = [
                    {
                        'obj_pk': obj_pk,
                        'field': field_name,
                        'related_pks': related_pks,
                    }
                    for obj_pk, related_pks in grouped.items()
                ]

            if include_history:
                _export_history_tables(cursor, payload)
    finally:
        conn.close()

    return payload


def _export_history_tables(cursor, payload):
    from django.apps import apps

    history_specs = [
        ('orders', 'HistoricalOrder', 'orders_historicalorder'),
        ('orders', 'HistoricalOrderItem', 'orders_historicalorderitem'),
        ('orders', 'HistoricalStatistics', 'orders_historicalstatistics'),
    ]
    for app_label, model_name, table_name in history_specs:
        if not _table_exists(cursor, table_name):
            continue
        model = apps.get_model(app_label, model_name)
        label = _model_label(model)
        source_cols = _table_columns(cursor, table_name)
        skip = {'history_id', 'restaurant_id'}
        field_map = {}
        for field in model._meta.fields:
            if field.name in skip or field.name == 'id':
                continue
            if field.is_relation and not field.many_to_many:
                if field.column in source_cols:
                    field_map[field.name] = field.column
            elif field.column in source_cols:
                field_map[field.name] = field.column

        cursor.execute(f'SELECT * FROM {table_name} ORDER BY history_id')
        records = []
        for row in cursor.fetchall():
            data = {'_pk': row['history_id']}
            for field_name, col in field_map.items():
                data[field_name] = _serialize_value(row.get(col))
            records.append(data)
        payload['models'][label] = records
