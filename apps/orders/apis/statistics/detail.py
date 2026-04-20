from decimal import Decimal

from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order, Statistics
from apps.payments.models import Payment


class StatisticsDetailAPIView(APIView):
    """
    API endpoint to get detailed information about a specific shift/statistics record.
    
    This includes:
    - Ümumi Məlumat (General Information): Basic shift data
    - Mabləğlər (Amounts): Cash, card, other payment totals
    - Nöbvə Detalları (Shift Details): Start/end times, who started/ended
    - Qeydlər və Hesabatlar (Notes and Reports): Connection data, order counts
    - Statistics-order əlaqələri (Statistics-Order Relations): Related orders table
    
    Path parameter:
    - shift_id: ID of the statistics/shift record
    
    Returns:
    - Detailed shift information with all tabs data
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, shift_id):
        try:
            shift = Statistics.objects.select_related(
                'started_by', 'ended_by'
            ).prefetch_related(
                'orders',
                'orders__table',
                'orders__waitress',
                'orders__order_items',
                'orders__order_items__meal'
            ).get(id=shift_id, title='till_now')
        except Statistics.DoesNotExist:
            return Response(
                {"error": "Hesabat tapılmadı"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Refresh calculations for open shift
        if not shift.is_closed:
            Statistics.objects.calculate_till_now(shift.started_by)
            shift.refresh_from_db()

        # === Ümumi Məlumat (General Information) Tab ===
        general_info = {
            'başlıq': shift.get_title_display(),
            'ümumi_məbləğ': str(shift.total),
            'tarix': str(shift.date),
            'hesabat_təsdiqləndi': shift.is_z_checked,
        }

        # === Mabləğlər (Amounts) Tab ===
        amounts_info = {
            'başlanğıc_nağd': str(shift.initial_cash),
            'başlanğıc_kart': str(shift.initial_card),
            'başlanğıc_digər': str(shift.initial_other),
            'nağd_qazanılmış': str(shift.cash_total),
            'kart_ümumi': str(shift.card_total),
            'digər_ödənişlər': str(shift.other_total),
            'çıxarılan_nağd': str(shift.withdrawn_amount),
            'çıxarılan_kart': str(shift.withdrawn_from_card),
            'çıxarılan_digər': str(shift.withdrawn_from_other),
            'qalan_nağd': str(shift.remaining_cash),
            'qalan_kart': str(shift.remaining_card),
            'qalan_digər': str(shift.remaining_other),
            'ümumi_əldə_olan_nağd': str(shift.cash_total + shift.initial_cash),
            'ümumi_çıxarılan': str(shift.withdrawn_amount + shift.withdrawn_from_card + shift.withdrawn_from_other),
        }

        # === Nöbvə Detalları (Shift Details) Tab ===
        shift_details = {
            'növbəni_açan': {
                'istifadəçi_adı': shift.started_by.username if shift.started_by else None,
                'tam_ad': f"{shift.started_by.first_name} {shift.started_by.last_name}".strip() if shift.started_by else None,
            },
            'başlanma_vaxtı': shift.start_time.isoformat() if shift.start_time else None,
            'növbəni_bağlayan': {
                'istifadəçi_adı': shift.ended_by.username if shift.ended_by else None,
                'tam_ad': f"{shift.ended_by.first_name} {shift.ended_by.last_name}".strip() if shift.ended_by else None,
            } if shift.ended_by else None,
            'bitmə_vaxtı': shift.end_time.isoformat() if shift.end_time else None,
            'növbə_bağlandı': shift.is_closed,
            'başlanma_qeydi': shift.notes,
            'bağlanma_qeydi': shift.withdrawn_notes,
        }

        # Calculate shift duration
        if shift.start_time and shift.end_time:
            duration = shift.end_time - shift.start_time
            hours = duration.total_seconds() / 3600
            shift_details['növbə_müddəti_saat'] = round(hours, 2)
        else:
            shift_details['növbə_müddəti_saat'] = None

        # === Statistics-Order əlaqələri (Order Relations) Tab ===
        orders = shift.orders.all()
        
        # Calculate per-waitress statistics
        waitress_stats = {}
        for order in orders:
            if order.waitress:
                waitress_key = order.waitress.username
                if waitress_key not in waitress_stats:
                    waitress_stats[waitress_key] = {
                        'ofisiant': f"{order.waitress.first_name} {order.waitress.last_name}".strip() or order.waitress.username,
                        'ümumi_məbləğ': Decimal('0.00'),
                        'sifariş_sayı': 0,
                    }
                waitress_stats[waitress_key]['ümumi_məbləğ'] += order.total_price
                waitress_stats[waitress_key]['sifariş_sayı'] += 1

        # Convert to list and format
        per_waitress = [
            {
                'ofisiant': stats['ofisiant'],
                'ümumi_məbləğ': f"{stats['ümumi_məbləğ']} AZN",
                'sifariş_sayı': stats['sifariş_sayı'],
            }
            for stats in waitress_stats.values()
        ]

        # Get connection data (bağlanma qeydi)
        connection_data = {
            'bağlanma_qeydi': 'maas-35\nrasxod nəqd-91' if shift.is_closed else '',
            'başlanma_qeydi': shift.notes or '',
            'display_per_waitress': per_waitress,
        }

        # Order items summary
        order_items_summary = []
        meal_totals = {}
        
        for order in orders:
            for item in order.order_items.all():
                meal_name = item.meal.name
                if meal_name not in meal_totals:
                    meal_totals[meal_name] = {
                        'yemək': meal_name,
                        'say': 0,
                        'qiymət': item.meal.price,
                        'ümumi': Decimal('0.00'),
                    }
                meal_totals[meal_name]['say'] += item.quantity
                meal_totals[meal_name]['ümumi'] += item.price

        order_items_summary = [
            {
                'yemək': data['yemək'],
                'say': data['say'],
                'vahid_qiymət': f"{data['qiymət']} AZN",
                'ümumi': f"{data['ümumi']} AZN",
            }
            for data in meal_totals.values()
        ]

        # Statistics-order əlaqələri table
        statistics_orders = []
        for order in orders:
            statistics_orders.append({
                'id': order.id,
                'stol': str(order.table),
                'məbləğ': f"{order.total_price} AZN",
                'ödənilib': order.is_paid,
                'yaradılma_tarixi': order.created_at.isoformat() if order.created_at else None,
            })

        # === Qeydlər və Hesabatlar (Notes and Reports) Tab ===
        notes_and_reports = {
            'bağlanma_qeydi': connection_data,
            'ofisiantların_xidməti': per_waitress,
            'sifariş_məhsulları_xülasəsi': order_items_summary,
        }

        # Response data
        data = {
            'ümumi_məlumat': general_info,
            'mabləğlər': amounts_info,
            'növbə_detalları': shift_details,
            'qeydlər_və_hesabatlar': notes_and_reports,
            'statistics_order_əlaqələri': statistics_orders,
        }

        return Response(data, status=status.HTTP_200_OK)
        return Response(data, status=status.HTTP_200_OK)
