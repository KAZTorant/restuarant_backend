"""Sales analytics for the admin panel dashboard."""

from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncHour
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_api.permissions import IsAdminUser
from apps.orders.models import Order, OrderItem
from apps.tenants.models import Restaurant

MONEY = Decimal('0.01')
TOP_LIMIT = 10
MAX_RANGE_DAYS = 92


def _money(value):
    amount = value if isinstance(value, Decimal) else Decimal(value or 0)
    return float(amount.quantize(MONEY, rounding=ROUND_HALF_UP))


def _share(part, whole):
    if not whole:
        return 0.0
    return round(float(part) / float(whole) * 100, 1)


def _person_name(first_name, last_name, username):
    full = f'{first_name or ""} {last_name or ""}'.strip()
    return full or username or 'Təyin edilməyib'


def _table_name(number, room_name, table_id):
    label = f'Stol {number}' if number else f'Stol #{table_id}'
    if room_name:
        return f'{room_name} · {label}'
    return label


def sales_analytics_payload(user, params):
    return AnalyticsDashboardView().build(user, params)


def _restaurant_scope(user, requested_id):
    """Staff always sees only their restaurant. Superuser must pick one."""
    if user.is_superuser:
        restaurants = list(Restaurant.objects.order_by('name').values('id', 'name'))
        if requested_id in (None, ''):
            return None, restaurants, True, 'Baxmaq üçün restoran seçin'
        try:
            restaurant_id = int(requested_id)
        except (TypeError, ValueError) as exc:
            raise ValueError('Restoran seçimi yanlışdır') from exc
        match = next((row for row in restaurants if row['id'] == restaurant_id), None)
        if match is None:
            raise ValueError('Restoran tapılmadı')
        return match, restaurants, False, ''

    restaurant = user.restaurant if getattr(user, 'restaurant_id', None) else None
    if restaurant is None:
        return None, [], False, 'Bu istifadəçiyə restoran bağlı deyil'
    return {'id': restaurant.pk, 'name': restaurant.name}, [], False, ''


class AnalyticsDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            return Response(self.build(request.user, request.query_params))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def build(self, user, params):
        try:
            range_key, start, end, label = self._bounds(params)
        except ValueError:
            raise

        restaurant, restaurants, needs_restaurant, scope_message = _restaurant_scope(
            user, params.get('restaurant')
        )
        paid_only = params.get('paid') in ('1', 'true', 'yes')
        if restaurant is None:
            return self._empty(
                range_key, start, end, label, paid_only,
                restaurant, restaurants, needs_restaurant, scope_message,
            )

        items = (
            OrderItem.objects
            .annotate(sold_at=Coalesce('item_added_at', 'created_at'))
            .filter(
                sold_at__gte=start,
                sold_at__lte=end,
                order__table__room__restaurant_id=restaurant['id'],
            )
        )
        if paid_only:
            items = items.filter(order__is_paid=True)

        totals = items.aggregate(
            revenue=Sum('price'),
            quantity=Sum('quantity'),
            orders=Count('order_id', distinct=True),
        )
        revenue = totals['revenue'] or Decimal('0')
        quantity = int(totals['quantity'] or 0)
        order_count = int(totals['orders'] or 0)

        order_ids = items.values_list('order_id', flat=True).distinct()
        orders = Order.objects.filter(pk__in=order_ids)
        customers = int(orders.aggregate(total=Sum('customer_count'))['total'] or 0)
        avg_order = (revenue / order_count) if order_count else Decimal('0')
        hourly = (end - start) <= timedelta(hours=36)

        payload = self._empty(
            range_key, start, end, label, paid_only,
            restaurant, restaurants, needs_restaurant, scope_message,
        )
        payload['hourly'] = hourly
        payload['kpis'] = {
            'revenue': _money(revenue),
            'quantity': quantity,
            'orders': order_count,
            'avg_order': _money(avg_order),
            'customers': customers,
        }
        payload['trend'] = self._trend(items, start, end, hourly)
        payload['products'] = self._products(items, revenue, quantity)
        payload['tables'] = self._tables(items, orders, revenue)
        payload['waiters'] = self._waiters(items, orders, revenue)
        return payload

    def _empty(self, range_key, start, end, label, paid_only, restaurant, restaurants, needs_restaurant, scope_message):
        hourly = (end - start) <= timedelta(hours=36)
        return {
            'range': range_key,
            'label': label,
            'paid_only': paid_only,
            'start': timezone.localtime(start).strftime('%Y-%m-%dT%H:%M'),
            'end': timezone.localtime(end).strftime('%Y-%m-%dT%H:%M'),
            'start_date': timezone.localtime(start).date().isoformat(),
            'end_date': timezone.localtime(end).date().isoformat(),
            'hourly': hourly,
            'needs_restaurant': needs_restaurant,
            'scope_message': scope_message,
            'restaurant': restaurant,
            'restaurants': restaurants,
            'kpis': {
                'revenue': 0.0,
                'quantity': 0,
                'orders': 0,
                'avg_order': 0.0,
                'customers': 0,
            },
            'trend': [],
            'products': [],
            'tables': [],
            'waiters': [],
        }

    def _bounds(self, params):
        range_key = (params.get('range') or 'day').strip().lower()
        now = timezone.localtime()
        tz = timezone.get_current_timezone()

        if range_key == 'week':
            start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
            return range_key, start, now, 'Son həftə'
        if range_key == 'month':
            start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
            return range_key, start, now, 'Son ay'
        if range_key == 'custom':
            start_raw = params.get('start') or ''
            end_raw = params.get('end') or ''
            try:
                start_day = datetime.strptime(start_raw, '%Y-%m-%d').date()
                end_day = datetime.strptime(end_raw, '%Y-%m-%d').date()
            except ValueError as exc:
                raise ValueError('Tarix formatı YYYY-MM-DD olmalıdır') from exc
            if start_day > end_day:
                raise ValueError('Başlanğıc tarixi bitiş tarixindən əvvəl olmalıdır')
            if (end_day - start_day).days > MAX_RANGE_DAYS:
                raise ValueError(f'Tarix aralığı {MAX_RANGE_DAYS} gündən çox ola bilməz')
            start = timezone.make_aware(datetime.combine(start_day, time.min), tz)
            end = timezone.make_aware(datetime.combine(end_day, time.max), tz)
            if end > now:
                end = now
            label = f'{start_day.strftime("%d.%m.%Y")} — {end_day.strftime("%d.%m.%Y")}'
            return range_key, start, end, label

        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return 'day', start, now, 'Son gün'

    def _trend(self, items, start, end, hourly):
        tz = timezone.get_current_timezone()
        if hourly:
            rows = (
                items.annotate(bucket=TruncHour('sold_at', tzinfo=tz))
                .values('bucket')
                .annotate(
                    revenue=Sum('price'),
                    quantity=Sum('quantity'),
                    orders=Count('order_id', distinct=True),
                )
            )
            lookup = {}
            for row in rows:
                bucket = row['bucket']
                if bucket is None:
                    continue
                local = timezone.localtime(bucket)
                lookup[(local.date(), local.hour)] = row

            points = []
            cursor = timezone.localtime(start).replace(minute=0, second=0, microsecond=0)
            last = timezone.localtime(end).replace(minute=0, second=0, microsecond=0)
            while cursor <= last:
                row = lookup.get((cursor.date(), cursor.hour))
                points.append(self._point(cursor.strftime('%H:%M'), row))
                cursor += timedelta(hours=1)
            return points

        rows = (
            items.annotate(bucket=TruncDate('sold_at', tzinfo=tz))
            .values('bucket')
            .annotate(
                revenue=Sum('price'),
                quantity=Sum('quantity'),
                orders=Count('order_id', distinct=True),
            )
        )
        lookup = {row['bucket']: row for row in rows if row['bucket']}
        points = []
        cursor = timezone.localtime(start).date()
        last = timezone.localtime(end).date()
        while cursor <= last:
            points.append(self._point(cursor.strftime('%d.%m'), lookup.get(cursor)))
            cursor += timedelta(days=1)
        return points

    def _point(self, label, row):
        if not row:
            return {'label': label, 'revenue': 0.0, 'quantity': 0, 'orders': 0}
        return {
            'label': label,
            'revenue': _money(row['revenue']),
            'quantity': int(row['quantity'] or 0),
            'orders': int(row['orders'] or 0),
        }

    def _products(self, items, revenue, quantity):
        rows = (
            items.values('meal_id', 'meal__name')
            .annotate(quantity=Sum('quantity'), revenue=Sum('price'))
            .order_by('-quantity', '-revenue')[:TOP_LIMIT]
        )
        result = []
        for row in rows:
            qty = int(row['quantity'] or 0)
            amount = row['revenue'] or Decimal('0')
            result.append({
                'id': row['meal_id'],
                'name': row['meal__name'] or 'Naməlum məhsul',
                'quantity': qty,
                'revenue': _money(amount),
                'share': _share(amount, revenue),
                'qty_share': _share(qty, quantity),
            })
        return result

    def _tables(self, items, orders, revenue):
        customers = {
            row['table_id']: int(row['customers'] or 0)
            for row in orders.values('table_id').annotate(customers=Sum('customer_count'))
        }
        rows = (
            items.values('order__table_id', 'order__table__number', 'order__table__room__name')
            .annotate(
                orders=Count('order_id', distinct=True),
                revenue=Sum('price'),
                quantity=Sum('quantity'),
            )
            .order_by('-orders', '-revenue')[:TOP_LIMIT]
        )
        result = []
        for row in rows:
            amount = row['revenue'] or Decimal('0')
            table_id = row['order__table_id']
            result.append({
                'id': table_id,
                'name': _table_name(
                    row['order__table__number'],
                    row['order__table__room__name'],
                    table_id,
                ),
                'orders': int(row['orders'] or 0),
                'quantity': int(row['quantity'] or 0),
                'customers': customers.get(table_id, 0),
                'revenue': _money(amount),
                'share': _share(amount, revenue),
            })
        return result

    def _waiters(self, items, orders, revenue):
        customers = {
            row['waitress_id']: int(row['customers'] or 0)
            for row in orders.values('waitress_id').annotate(customers=Sum('customer_count'))
        }
        rows = (
            items.values(
                'order__waitress_id',
                'order__waitress__first_name',
                'order__waitress__last_name',
                'order__waitress__username',
            )
            .annotate(
                orders=Count('order_id', distinct=True),
                revenue=Sum('price'),
                quantity=Sum('quantity'),
            )
            .order_by('-orders', '-revenue')[:TOP_LIMIT]
        )
        result = []
        for row in rows:
            amount = row['revenue'] or Decimal('0')
            waitress_id = row['order__waitress_id']
            result.append({
                'id': waitress_id,
                'name': _person_name(
                    row['order__waitress__first_name'],
                    row['order__waitress__last_name'],
                    row['order__waitress__username'],
                ) if waitress_id else 'Təyin edilməyib',
                'orders': int(row['orders'] or 0),
                'quantity': int(row['quantity'] or 0),
                'customers': customers.get(waitress_id, 0),
                'revenue': _money(amount),
                'share': _share(amount, revenue),
            })
        return result
