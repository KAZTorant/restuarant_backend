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
    ('inventory', 'Category'),
    ('inventory', 'Supplier'),
    ('inventory', 'InventoryItem'),
    ('inventory', 'InventoryRecord'),
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
    ('orders', 'HistoricalOrder'),
    ('orders', 'HistoricalOrderItem'),
    ('orders', 'HistoricalStatistics'),
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

HISTORY_PK_FIELD = {
    'orders.HistoricalOrder': 'history_id',
    'orders.HistoricalOrderItem': 'history_id',
    'orders.HistoricalStatistics': 'history_id',
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


def _auto_timestamp_values(model, create_data):
    """auto_now / auto_now_add sahələri create() zamanı indi-yə yazılır.

    Dump-dakı orijinal vaxtı sonra update ilə bərpa etmək üçün ayırırıq.
    """
    preserved = {}
    for field in model._meta.fields:
        if not (getattr(field, 'auto_now', False) or getattr(field, 'auto_now_add', False)):
            continue
        if field.attname in create_data:
            value = create_data[field.attname]
        elif field.name in create_data:
            value = create_data[field.name]
        else:
            continue
        if value is not None:
            preserved[field.attname] = value
    return preserved


def _restore_auto_timestamps(model, objects):
    if not objects:
        return
    fields = sorted({
        name
        for obj in objects
        for name in getattr(obj, '_preserved_auto_fields', ())
    })
    if not fields:
        return
    model.objects.bulk_update(objects, fields, batch_size=500)
    for obj in objects:
        if hasattr(obj, '_preserved_auto_fields'):
            del obj._preserved_auto_fields


def _normalize_payload_duplicates(payload):
    """Importdan əvvəl eyni kateqoriyada təkrarlanan yemək adlarını düzəldir."""
    meals = payload.get('models', {}).get('meals.meal', [])
    seen = {}
    for record in meals:
        name = (record.get('name') or '').strip()
        category_id = record.get('category')
        key = (category_id, name.lower())
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count > 1:
            record['name'] = f'{name} ({count})'


@transaction.atomic
def import_restaurant_data(restaurant, payload):
    """Import exported JSON data into a restaurant tenant."""
    if payload.get('version') != 1:
        raise ValueError('Dəstəklənməyən export versiyası.')

    _normalize_payload_duplicates(payload)
    id_map = {}

    def remap(label, old_pk):
        if old_pk is None:
            return None
        return id_map.get(f'{label}:{old_pk}')

    def fallback_user_pk():
        cached = id_map.get('_fallback_user_pk')
        if cached:
            return cached
        user_model = apps.get_model('users', 'User')
        fallback = user_model.objects.filter(restaurant=restaurant).order_by('pk').first()
        if fallback:
            id_map['_fallback_user_pk'] = fallback.pk
            return fallback.pk
        return None

    for app_label, model_name in EXPORT_ORDER:
        model = apps.get_model(app_label, model_name)
        label = _model_label(model)
        records = payload.get('models', {}).get(label, [])

        stamped_objects = []
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
                    fk_value = remap(related_label, record[field.name])
                    if (
                        fk_value is None
                        and record.get(field.name) is not None
                        and field.related_model._meta.label_lower == 'users.user'
                    ):
                        fk_value = fallback_user_pk()
                    create_data[field.attname] = fk_value
                elif field.name == 'restaurant':
                    create_data[field.name] = restaurant
                else:
                    create_data[field.name] = _parse_value(field, record[field.name])

            if hasattr(model, 'restaurant_id') and 'restaurant' not in create_data:
                create_data['restaurant'] = restaurant

            history_key = f'{app_label}.{model_name}'
            if history_key in HISTORY_PK_FIELD:
                create_data[HISTORY_PK_FIELD[history_key]] = old_pk

            skip = False
            for field in model._meta.fields:
                if field.primary_key or field.many_to_many:
                    continue
                if field.is_relation and not field.null and create_data.get(field.attname) is None:
                    if field.name in record and record[field.name] is not None:
                        skip = True
                        break
            if skip:
                continue

            preserved = _auto_timestamp_values(model, create_data)
            obj = model.objects.create(**create_data)
            if preserved:
                for field_name, value in preserved.items():
                    setattr(obj, field_name, value)
                obj._preserved_auto_fields = tuple(preserved)
                stamped_objects.append(obj)
            pk_field = HISTORY_PK_FIELD.get(history_key, 'pk')
            new_pk = getattr(obj, pk_field)
            id_map[f'{label}:{old_pk}'] = new_pk

        _restore_auto_timestamps(model, stamped_objects)

    _dedupe_meal_names(restaurant)
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


def _dedupe_meal_names(restaurant):
    """Importdan sonra eyni kateqoriyada təkrarlanan yemək adlarını düzəldir."""
    from apps.meals.models import Meal

    meals = Meal.objects.filter(
        category__group__restaurant=restaurant,
    ).order_by('category_id', 'name', 'pk')

    seen = {}
    for meal in meals:
        key = (meal.category_id, meal.name.lower())
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count > 1:
            meal.name = f'{meal.name} ({count})'
            meal.save(update_fields=['name'])


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
