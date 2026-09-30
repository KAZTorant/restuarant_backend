"""Dump importunun eyni vaxta vurduğu tarixləri bərpa edir."""

import gzip
import json
from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncMinute
from django.utils.dateparse import parse_datetime
from django.utils import timezone

# Normal növbədə bir dəqiqədə bu qədər ödəniş olmur. Bu hədd import dalğasını ayırır.
IMPORT_BURST_PER_MINUTE = 30

from apps.orders.models import Order, Statistics
from apps.payments.admin.payment_calculation import recalculate_payment_calculation
from apps.payments.models import Payment, PaymentCalculation, PaymentMethod
from apps.tenants.models import Restaurant


def _parse_dt(value):
    if not value:
        return None
    parsed = parse_datetime(value) if isinstance(value, str) else value
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def _table_keys(payload):
    rooms = {
        room['_pk']: room.get('name') or ''
        for room in payload.get('models', {}).get('tables.room', [])
    }
    tables = {}
    for table in payload.get('models', {}).get('tables.table', []):
        number = (table.get('number') or '').strip().lower()
        tables[table['_pk']] = (rooms.get(table.get('room')), number)
    return tables


def _db_table_key(room_name, number):
    return (room_name or '', (number or '').strip().lower())


def _import_cluster_pks(queryset, field_name):
    """Importun eyni dəqiqəyə vurduğu sətirlərin pk-ları.

    Belə dalğa yoxdursa None qaytarır və bütün sətirlər tutuşdurulur.
    Sonradan yaradılmış ödənişlər bu çoxluğa düşmür.
    """
    rows = list(
        queryset.annotate(minute=TruncMinute(field_name))
        .values('minute')
        .annotate(total=Count('pk'))
    )
    burst_minutes = [
        row['minute']
        for row in rows
        if row['minute'] is not None and row['total'] >= IMPORT_BURST_PER_MINUTE
    ]
    if not burst_minutes:
        return None

    window = Q()
    for minute in burst_minutes:
        window |= Q(**{
            f'{field_name}__gte': minute,
            f'{field_name}__lt': minute + timedelta(minutes=1),
        })
    return set(queryset.filter(window).values_list('pk', flat=True))


class Command(BaseCommand):
    help = (
        'Dump importu zamanı indi-yə yazılmış ödəniş, sifariş və '
        'hesabat başlama tarixlərini orijinal JSON dump-dan bərpa edir.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--restaurant', default='qonaq-baku')
        parser.add_argument('--data-path', default='data/qonaq_baku.json.gz')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Yazmadan uyğunluğu yoxlayır',
        )

    def handle(self, *args, **options):
        restaurant = Restaurant.objects.filter(slug=options['restaurant']).first()
        if restaurant is None:
            raise CommandError(f"Restoran tapılmadı: {options['restaurant']}")

        path = options['data_path']
        opener = gzip.open if path.endswith('.gz') else open
        with opener(path, 'rt', encoding='utf-8') as handle:
            payload = json.load(handle)

        tables = _table_keys(payload)
        with transaction.atomic():
            payment_map, payment_stats = self._restore_payments(restaurant, payload, tables)
            if payment_stats.get('no_burst'):
                self.stdout.write(self.style.WARNING(
                    'Ödəniş import dalğası tapılmadı. Ödəniş tarixləri dəyişdirilmədi.'
                ))
                order_stats = {'restored': 0, 'skipped': 0, 'untouched': 0}
                method_stats = {'restored': 0, 'skipped': 0}
                refreshed = 0
            else:
                order_stats = self._restore_orders(restaurant, payload, tables)
                method_stats = self._restore_payment_methods(payload, payment_map)
                refreshed = self._refresh_calculations(restaurant)

            stat_stats = self._restore_statistics(restaurant, payload)

            self.stdout.write(
                f"Ödənişlər: {payment_stats['restored']} bərpa, "
                f"{payment_stats['skipped']} uyğun gəlmədi, "
                f"{payment_stats['untouched']} sonrakı ödəniş toxunulmadı"
            )
            self.stdout.write(
                f"Sifarişlər: {order_stats['restored']} bərpa, "
                f"{order_stats['skipped']} uyğun gəlmədi, "
                f"{order_stats['untouched']} sonrakı sifariş toxunulmadı"
            )
            self.stdout.write(
                f"Ödəniş növləri: {method_stats['restored']} bərpa, "
                f"{method_stats['skipped']} uyğun gəlmədi"
            )
            self.stdout.write(f"Yenilənən hesablama: {refreshed}")
            if stat_stats.get('no_burst'):
                self.stdout.write(self.style.WARNING(
                    'Hesabat import dalğası tapılmadı. Başlama vaxtları dəyişdirilmədi.'
                ))
            else:
                self.stdout.write(
                    f"Hesabatlar: {stat_stats['restored']} başlama vaxtı bərpa, "
                    f"{stat_stats['skipped']} uyğun gəlmədi, "
                    f"{stat_stats['untouched']} sonrakı hesabat toxunulmadı"
                )

            if options['dry_run']:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('Dry-run: dəyişiklik yazılmadı.'))
            else:
                self.stdout.write(self.style.SUCCESS('Tarixlər bərpa olundu.'))

    def _restore_payments(self, restaurant, payload, tables):
        grouped = defaultdict(list)
        for record in payload.get('models', {}).get('payments.payment', []):
            grouped[tables.get(record.get('table'))].append(record)

        base_qs = Payment.objects.filter(table__room__restaurant=restaurant)
        cluster_pks = _import_cluster_pks(base_qs, 'paid_at')
        if cluster_pks is None:
            return {}, {
                'restored': 0,
                'skipped': 0,
                'untouched': base_qs.count(),
                'no_burst': True,
            }
        db_grouped = defaultdict(list)
        untouched = 0
        rows = base_qs.order_by('pk').values_list(
            'pk', 'table__room__name', 'table__number', 'final_price', 'paid_amount',
        )
        for pk, room_name, number, final_price, paid_amount in rows:
            if cluster_pks is not None and pk not in cluster_pks:
                untouched += 1
                continue
            db_grouped[_db_table_key(room_name, number)].append(
                (pk, str(final_price), str(paid_amount))
            )

        updates = []
        payment_map = {}
        skipped = 0
        for key, records in grouped.items():
            db_rows = db_grouped.get(key, [])
            if len(records) != len(db_rows):
                skipped += len(records)
                continue
            aligned = True
            for record, db_row in zip(records, db_rows):
                if str(record.get('final_price')) != db_row[1] or str(record.get('paid_amount')) != db_row[2]:
                    aligned = False
                    break
            if not aligned:
                skipped += len(records)
                continue
            for record, db_row in zip(records, db_rows):
                paid_at = _parse_dt(record.get('paid_at'))
                if paid_at is None:
                    skipped += 1
                    continue
                updates.append(Payment(pk=db_row[0], paid_at=paid_at))
                payment_map[record['_pk']] = db_row[0]

        if updates:
            Payment.objects.bulk_update(updates, ['paid_at'], batch_size=1000)
        return payment_map, {
            'restored': len(updates),
            'skipped': skipped,
            'untouched': untouched,
        }

    def _restore_orders(self, restaurant, payload, tables):
        grouped = defaultdict(list)
        for record in payload.get('models', {}).get('orders.order', []):
            grouped[tables.get(record.get('table'))].append(record)

        base_qs = Order.objects.all_orders().filter(table__room__restaurant=restaurant)
        cluster_pks = _import_cluster_pks(base_qs, 'created_at')
        if cluster_pks is None:
            return {'restored': 0, 'skipped': 0, 'untouched': base_qs.count()}
        db_grouped = defaultdict(list)
        untouched = 0
        rows = base_qs.order_by('pk').values_list(
            'pk', 'table__room__name', 'table__number', 'total_price', 'is_paid',
        )
        for pk, room_name, number, total_price, is_paid in rows:
            if cluster_pks is not None and pk not in cluster_pks:
                untouched += 1
                continue
            db_grouped[_db_table_key(room_name, number)].append(
                (pk, str(total_price), bool(is_paid))
            )

        updates = []
        skipped = 0
        for key, records in grouped.items():
            db_rows = db_grouped.get(key, [])
            if len(records) != len(db_rows):
                skipped += len(records)
                continue
            aligned = True
            for record, db_row in zip(records, db_rows):
                if str(record.get('total_price')) != db_row[1] or bool(record.get('is_paid')) != db_row[2]:
                    aligned = False
                    break
            if not aligned:
                skipped += len(records)
                continue
            for record, db_row in zip(records, db_rows):
                created_at = _parse_dt(record.get('created_at'))
                updated_at = _parse_dt(record.get('updated_at'))
                if created_at is None:
                    skipped += 1
                    continue
                updates.append(Order(
                    pk=db_row[0],
                    created_at=created_at,
                    updated_at=updated_at or created_at,
                ))

        if updates:
            Order.objects.all_orders().bulk_update(
                updates, ['created_at', 'updated_at'], batch_size=1000,
            )
        return {
            'restored': len(updates),
            'skipped': skipped,
            'untouched': untouched,
        }

    def _restore_payment_methods(self, payload, payment_map):
        grouped = defaultdict(list)
        for record in payload.get('models', {}).get('payments.paymentmethod', []):
            grouped[record.get('payment')].append(record)

        new_ids = list(payment_map.values())
        db_grouped = defaultdict(list)
        if new_ids:
            rows = PaymentMethod.objects.filter(payment_id__in=new_ids).order_by('pk').values_list(
                'pk', 'payment_id', 'amount', 'payment_type',
            )
            for pk, payment_id, amount, payment_type in rows:
                db_grouped[payment_id].append((pk, str(amount), payment_type or ''))

        updates = []
        skipped = 0
        for old_payment_id, records in grouped.items():
            new_payment_id = payment_map.get(old_payment_id)
            if not new_payment_id:
                skipped += len(records)
                continue
            db_rows = db_grouped.get(new_payment_id, [])
            if len(records) != len(db_rows):
                skipped += len(records)
                continue
            aligned = True
            for record, db_row in zip(records, db_rows):
                if str(record.get('amount')) != db_row[1] or (record.get('payment_type') or '') != db_row[2]:
                    aligned = False
                    break
            if not aligned:
                skipped += len(records)
                continue
            for record, db_row in zip(records, db_rows):
                created_at = _parse_dt(record.get('created_at'))
                if created_at is None:
                    skipped += 1
                    continue
                updates.append(PaymentMethod(pk=db_row[0], created_at=created_at))

        if updates:
            PaymentMethod.objects.bulk_update(updates, ['created_at'], batch_size=1000)
        return {'restored': len(updates), 'skipped': skipped}

    def _restore_statistics(self, restaurant, payload):
        """start_time auto_now_add olduğu üçün import hamısını eyni vaxta vurur.

        Bitmə vaxtı importda qorunur və hesabatı dump sətri ilə tutuşdurur.
        Açıq növbədə bitmə vaxtı boşdur; onu başlanğıc məbləğləri ayırır.
        """
        records = payload.get('models', {}).get('orders.statistics', [])
        base_qs = Statistics.objects.filter(restaurant=restaurant)
        cluster_pks = _import_cluster_pks(base_qs, 'start_time')
        if cluster_pks is None:
            return {
                'restored': 0,
                'skipped': 0,
                'untouched': base_qs.count(),
                'no_burst': True,
            }

        db_by_end = defaultdict(list)
        untouched = 0
        rows = base_qs.values_list(
            'pk', 'end_time', 'initial_cash', 'initial_card', 'initial_other',
        )
        for pk, end_time, initial_cash, initial_card, initial_other in rows:
            if pk not in cluster_pks:
                untouched += 1
                continue
            db_by_end[end_time].append({
                'pk': pk,
                'initials': (
                    str(initial_cash),
                    str(initial_card),
                    str(initial_other),
                ),
            })

        updates = []
        skipped = 0
        used = set()
        for record in records:
            end_time = _parse_dt(record.get('end_time'))
            start_time = _parse_dt(record.get('start_time'))
            created_at = _parse_dt(record.get('created_at')) or start_time
            if start_time is None:
                skipped += 1
                continue
            candidates = [
                row for row in db_by_end.get(end_time, [])
                if row['pk'] not in used
            ]
            if end_time is None:
                initials = (
                    str(record.get('initial_cash')),
                    str(record.get('initial_card')),
                    str(record.get('initial_other')),
                )
                narrowed = [row for row in candidates if row['initials'] == initials]
                if len(narrowed) == 1:
                    candidates = narrowed
                elif len(candidates) != 1:
                    skipped += 1
                    continue
            elif len(candidates) != 1:
                skipped += 1
                continue
            row = candidates[0]
            used.add(row['pk'])
            updates.append(Statistics(
                pk=row['pk'],
                start_time=start_time,
                created_at=created_at,
            ))

        if updates:
            Statistics.objects.bulk_update(
                updates, ['start_time', 'created_at'], batch_size=500,
            )
        return {
            'restored': len(updates),
            'skipped': skipped,
            'untouched': untouched,
        }

    def _refresh_calculations(self, restaurant):
        count = 0
        for calculation in PaymentCalculation.objects.filter(restaurant=restaurant):
            recalculate_payment_calculation(calculation)
            count += 1
        return count
