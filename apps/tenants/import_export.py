import json
from datetime import date, datetime, time
from decimal import Decimal

from django.apps import apps
from django.db import transaction
from django.forms.models import model_to_dict

SKIP_FIELDS = {'id', 'last_login', 'date_joined'}
USER_SKIP_FIELDS = {'id', 'last_login', 'date_joined'}


def _serialize_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _model_label(model):
    return f'{model._meta.app_label}.{model._meta.model_name}'


EXPORT_ORDER = [
    ('users', 'User'),
    ('printers', 'Printer'),
    ('printers', 'PreparationPlace'),
    ('meals', 'MealGroup'),
    ('meals', 'MealCategory'),
    ('meals', 'Meal'),
    ('tables', 'Room'),
    ('tables', 'Table'),
    ('orders', 'WorkPeriodConfig'),
    ('users', 'WhatsAppConfig'),
    ('printers', 'PrintGatewayLocation'),
    ('orders', 'Statistics'),
    ('orders', 'Order'),
    ('orders', 'OrderItem'),
    ('payments', 'Payment'),
    ('payments', 'PaymentMethod'),
    ('finance', 'Income'),
    ('finance', 'Expense'),
    ('users', 'ShiftHandover'),
    ('orders', 'Summary'),
    ('orders', 'Report'),
    ('payments', 'PaymentCalculation'),
    ('inventory_connector', 'MealInventoryConnector'),
    ('inventory_connector', 'MealInventoryMapping'),
    ('printers', 'Receipt'),
    ('orders', 'OrderItemDeletionLog'),
]

M2M_FIELDS = {
    'meals.Meal': ['preparation_places'],
    'orders.Statistics': ['orders'],
    'orders.Summary': ['statistics'],
    'orders.Report': ['orders'],
    'payments.Payment': ['orders'],
    'payments.PaymentCalculation': ['payments'],
    'printers.Receipt': ['orders'],
    'inventory_connector.MealInventoryConnector': ['inventory_items'],
}


def export_restaurant_data(restaurant=None):
    """Export all tenant data as JSON. If restaurant is None, export legacy single-tenant data."""
    payload = {
        'version': 1,
        'exported_at': datetime.now().isoformat(),
        'restaurant_slug': restaurant.slug if restaurant else None,
        'models': {},
        'm2m': {},
    }

    for app_label, model_name in EXPORT_ORDER:
        model = apps.get_model(app_label, model_name)
        label = _model_label(model)
        qs = model.objects.all()
        if restaurant is not None and hasattr(model, 'restaurant_id'):
            qs = qs.filter(restaurant=restaurant)

        records = []
        for obj in qs.order_by('pk'):
            data = {}
            skip = USER_SKIP_FIELDS if model._meta.model_name == 'user' else SKIP_FIELDS
            for field in model._meta.fields:
                if field.name in skip:
                    continue
                if field.is_relation and not field.many_to_many:
                    data[field.name] = getattr(obj, f'{field.name}_id')
                else:
                    data[field.name] = _serialize_value(getattr(obj, field.name))
            data['_pk'] = obj.pk
            records.append(data)
        payload['models'][label] = records

        m2m_key = f'{app_label}.{model_name}'
        if m2m_key in M2M_FIELDS:
            m2m_data = []
            for obj in qs.order_by('pk'):
                for field_name in M2M_FIELDS[m2m_key]:
                    related_ids = list(
                        getattr(obj, field_name).values_list('pk', flat=True)
                    )
                    if related_ids:
                        m2m_data.append({
                            'obj_pk': obj.pk,
                            'field': field_name,
                            'related_pks': related_ids,
                        })
            if m2m_data:
                payload['m2m'][label] = m2m_data

    return payload


def _parse_value(field, value):
    if value is None:
        return None
    internal_type = field.get_internal_type()
    if internal_type in ('DateTimeField', 'DateField', 'TimeField'):
        if isinstance(value, str):
            if internal_type == 'DateField':
                return date.fromisoformat(value)
            if internal_type == 'TimeField':
                return time.fromisoformat(value)
            return datetime.fromisoformat(value)
    if internal_type in ('DecimalField', 'FloatField') and isinstance(value, str):
        return Decimal(value)
    return value


@transaction.atomic
def import_restaurant_data(restaurant, payload):
    """Import exported JSON data into a restaurant tenant."""
    if payload.get('version') != 1:
        raise ValueError('Dəstəklənməyən export versiyası.')

    id_map = {}

    def remap(label, old_pk):
        if old_pk is None:
            return None
        return id_map.get(f'{label}:{old_pk}')

    for app_label, model_name in EXPORT_ORDER:
        model = apps.get_model(app_label, model_name)
        label = _model_label(model)
        records = payload.get('models', {}).get(label, [])

        for record in records:
            old_pk = record.pop('_pk')
            create_data = {}

            for field in model._meta.fields:
                skip = USER_SKIP_FIELDS if model._meta.model_name == 'user' else SKIP_FIELDS
                if field.name in skip or field.name == 'id':
                    continue
                if field.name not in record:
                    continue
                if field.is_relation and not field.many_to_many:
                    related_label = _model_label(field.related_model)
                    create_data[field.name] = remap(related_label, record[field.name])
                elif field.name == 'restaurant':
                    create_data[field.name] = restaurant
                else:
                    create_data[field.name] = _parse_value(field, record[field.name])

            if hasattr(model, 'restaurant_id') and 'restaurant' not in create_data:
                create_data['restaurant'] = restaurant

            obj = model.objects.create(**create_data)
            id_map[f'{label}:{old_pk}'] = obj.pk

    _remap_deletion_log_ids(id_map)

    for label, m2m_entries in payload.get('m2m', {}).items():
        app_label, model_name = label.split('.')
        model = apps.get_model(app_label, model_name)
        for entry in m2m_entries:
            new_obj_pk = remap(label, entry['obj_pk'])
            if not new_obj_pk:
                continue
            obj = model.objects.get(pk=new_obj_pk)
            related_model = getattr(obj, entry['field']).model
            related_label = _model_label(related_model)
            new_related_pks = [
                remap(related_label, pk) for pk in entry['related_pks']
            ]
            getattr(obj, entry['field']).set(
                [pk for pk in new_related_pks if pk is not None]
            )

    return id_map


def _remap_deletion_log_ids(id_map):
    from apps.orders.models.order_deletion import OrderItemDeletionLog

    order_label = 'orders.order'
    item_label = 'orders.orderitem'
    table_label = 'tables.table'

    for log in OrderItemDeletionLog.objects.all():
        updates = {}
        new_order_id = id_map.get(f'{order_label}:{log.order_id}')
        new_item_id = id_map.get(f'{item_label}:{log.order_item_id}')
        new_table_id = id_map.get(f'{table_label}:{log.table_id}')
        if new_order_id:
            updates['order_id'] = new_order_id
        if new_item_id:
            updates['order_item_id'] = new_item_id
        if new_table_id:
            updates['table_id'] = new_table_id
        if updates:
            OrderItemDeletionLog.objects.filter(pk=log.pk).update(**updates)


def export_to_json_file(path, restaurant=None):
    payload = export_restaurant_data(restaurant)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def import_from_json_file(restaurant, path):
    with open(path, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    return import_restaurant_data(restaurant, payload)
