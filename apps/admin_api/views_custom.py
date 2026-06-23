"""Custom admin endpoints that mirror Django admin custom views."""

from datetime import datetime
from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_api.permissions import IsAdminUser
from apps.admin_api.registry import get_model_admin
from apps.orders.models import Order, Statistics, Summary
from apps.payments.models import Payment, PaymentCalculation
from apps.tenants.admin_utils import filter_queryset_by_restaurant, get_user_restaurant


class StatisticsCustomView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, action):
        handlers = {
            'active-orders': self._active_orders,
            'current-shift-info': self._current_shift_info,
            'start-shift-info': self._start_shift_info,
        }
        handler = handlers.get(action)
        if not handler:
            return Response({'detail': 'Unknown action'}, status=status.HTTP_404_NOT_FOUND)
        try:
            return Response(handler(request))
        except Http404:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, action):
        handlers = {
            'calculate-till-now': self._calculate_till_now,
            'calculate-daily': self._calculate_daily,
            'calculate-monthly': self._calculate_monthly,
            'calculate-yearly': self._calculate_yearly,
            'calculate-per-waitress': self._calculate_per_waitress,
            'start-shift': self._start_shift,
        }
        handler = handlers.get(action)
        if not handler:
            shift_id = request.data.get('shift_id')
            if action == 'end-shift' and shift_id:
                return Response(self._end_shift(request, shift_id))
            if action == 'print-shift-summary' and shift_id:
                return Response(self._print_shift_summary(request, shift_id))
            if action == 'print-order-items-summary' and shift_id:
                return Response(self._print_order_items_summary(request, shift_id))
            return Response({'detail': 'Unknown action'}, status=status.HTTP_404_NOT_FOUND)
        return Response(handler(request))

    def _active_orders(self, request):
        restaurant = get_user_restaurant(request.user)
        orders_qs = filter_queryset_by_restaurant(
            Order.objects.all(), restaurant, 'table__room__restaurant'
        )
        paid = orders_qs.filter(is_paid=True).aggregate(sum=Sum('total_price'))['sum'] or 0
        unpaid = orders_qs.filter(is_paid=False).aggregate(sum=Sum('total_price'))['sum'] or 0
        return {'total_paid': str(paid), 'total_unpaid': str(unpaid)}

    def _current_shift_info(self, request):
        Statistics.objects.calculate_till_now(request.user)
        shift = Statistics.objects.filter(started_by=request.user, is_closed=False).first()
        if not shift:
            raise Http404()
        return {
            'shift_id': shift.id,
            'cash_total': str(shift.cash_total),
            'card_total': str(shift.card_total),
            'other_total': str(shift.other_total),
            'total': str(shift.total),
            'cash_in_hand': str(shift.cash_total + shift.initial_cash),
            'initial_cash': str(shift.initial_cash),
            'initial_card': str(shift.initial_card),
            'initial_other': str(shift.initial_other),
        }

    def _start_shift_info(self, request):
        Statistics.objects.calculate_till_now(request.user)
        restaurant = get_user_restaurant(request.user)
        last = filter_queryset_by_restaurant(
            Statistics.objects.filter(is_closed=True), restaurant
        ).order_by('-end_time').first()
        if not last:
            return {'initial_cash': '0', 'initial_card': '0', 'initial_other': '0'}
        return {
            'initial_cash': str(last.remaining_cash),
            'initial_card': str(last.remaining_card),
            'initial_other': str(last.remaining_other),
        }

    def _calculate_till_now(self, request):
        Statistics.objects.calculate_till_now(request.user)
        return {'detail': 'Bu günə kimi statistika yeniləndi'}

    def _calculate_daily(self, request):
        Statistics.objects.calculate_daily()
        return {'detail': 'Günlük statistika əlavə edildi'}

    def _calculate_monthly(self, request):
        Statistics.objects.calculate_monthly()
        return {'detail': 'Aylıq statistika əlavə edildi'}

    def _calculate_yearly(self, request):
        Statistics.objects.calculate_yearly()
        return {'detail': 'İllik statistika əlavə edildi'}

    def _calculate_per_waitress(self, request):
        Statistics.objects.calculate_per_waitress()
        return {'detail': 'Ofisiant statistikası əlavə edildi'}

    def _start_shift(self, request):
        try:
            initial_cash = Decimal(request.data.get('initial_cash', '0') or '0')
            initial_card = Decimal(request.data.get('initial_card', '0') or '0')
            initial_other = Decimal(request.data.get('initial_other', '0') or '0')
            notes = request.data.get('notes', '')

            shift = Statistics.objects.start_shift(request.user)
            shift.initial_cash = initial_cash
            shift.initial_card = initial_card
            shift.initial_other = initial_other
            if notes:
                shift.notes = notes
            shift.save()

            Statistics.objects.calculate_till_now(request.user)
            return {'shift_id': shift.id, 'detail': 'Növbə başladıldı'}
        except ValidationError as e:
            return {'detail': str(e), 'error': True}

    def _end_shift(self, request, shift_id):
        shift = Statistics.objects.filter(pk=shift_id).first()
        if not shift:
            raise Http404()
        withdrawn = Decimal(request.data.get('withdrawn_amount', '0') or '0')
        withdrawn_notes = request.data.get('withdrawn_notes', '-') or '-'
        Statistics.objects.calculate_till_now()
        Statistics.objects.end_shift(shift, request.user, withdrawn, withdrawn_notes)
        shift.refresh_from_db()
        return {
            'detail': f'Növbə bağlandı. Qalan nağd: {shift.remaining_cash} AZN',
            'remaining_cash': str(shift.remaining_cash),
        }

    def _print_shift_summary(self, request, shift_id):
        from apps.printers.utils.service_v2 import PrinterService as PrinterServiceV2
        success, msg = PrinterServiceV2.print_shift_summary(stat_id=shift_id, user=request.user)
        return {'success': success, 'detail': msg}

    def _print_order_items_summary(self, request, shift_id):
        from apps.printers.utils.service_v2 import PrinterService as PrinterServiceV2
        success, msg = PrinterServiceV2.print_order_items_summary(stat_id=shift_id, user=request.user)
        return {'success': success, 'detail': msg}


class SummaryCustomView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, action):
        if action == 'create-summary':
            return Response(self._create_summary(request))
        return Response({'detail': 'Unknown action'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, action, pk=None):
        if action == 'preview-summary' and pk:
            return Response(self._preview_summary(request, pk))
        return Response({'detail': 'Unknown action'}, status=status.HTTP_404_NOT_FOUND)

    def _create_summary(self, request):
        _, model_admin = get_model_admin('orders', 'summary')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            if start > end:
                return Response({'detail': 'Başlanğıc tarixi bitiş tarixindən əvvəl olmalıdır'}, status=400)
        except (ValueError, TypeError):
            return Response({'detail': 'Tarix formatını yoxlayın'}, status=400)

        summary = model_admin.create_date_range_summary(request.user, start, end)
        if summary:
            return Response({'id': summary.id, 'detail': f'Hesabat yaradıldı: {start} - {end}'})
        return Response({'detail': 'Bu tarix aralığında məlumat tapılmadı'}, status=404)

    def _preview_summary(self, request, pk):
        summary = Summary.objects.filter(pk=pk).first()
        if not summary:
            raise Http404()
        return {
            'id': summary.id,
            'title': summary.title,
            'total': str(summary.total),
            'cash_total': str(summary.cash_total),
            'card_total': str(summary.card_total),
            'other_total': str(summary.other_total),
            'date_range': summary.date_range_display,
        }


class PaymentCalculationCustomView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, action):
        if action != 'calculate':
            return Response({'detail': 'Unknown action'}, status=status.HTTP_404_NOT_FOUND)

        from apps.payments.admin.payment_calculation import PaymentCalculationForm

        form = PaymentCalculationForm(request.data)
        if not form.is_valid():
            return Response({'errors': form.errors}, status=400)

        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        start_time = form.cleaned_data['start_time']
        end_time = form.cleaned_data['end_time']

        start_datetime = timezone.make_aware(datetime.combine(start_date, start_time))
        end_datetime = timezone.make_aware(datetime.combine(end_date, end_time))

        payments = filter_queryset_by_restaurant(
            Payment.objects.filter(paid_at__gte=start_datetime, paid_at__lte=end_datetime),
            get_user_restaurant(request.user),
            'table__room__restaurant',
        )

        total_amount = payments.aggregate(total=Sum('final_price'))['total'] or 0
        payment_count = payments.count()
        cash_amount = card_amount = other_amount = 0

        for payment in payments:
            if payment.payment_methods.exists():
                for method in payment.payment_methods.all():
                    if method.payment_type == 'cash':
                        cash_amount += method.amount
                    elif method.payment_type == 'card':
                        card_amount += method.amount
                    else:
                        other_amount += method.amount
            else:
                if payment.payment_type == 'cash':
                    cash_amount += payment.paid_amount
                elif payment.payment_type == 'card':
                    card_amount += payment.paid_amount
                else:
                    other_amount += payment.paid_amount

        restaurant = getattr(request.user, 'restaurant', None)
        if not restaurant and payments.exists():
            restaurant = payments.first().table.room.restaurant

        calc = PaymentCalculation.objects.create(
            restaurant=restaurant,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            total_amount=total_amount,
            payment_count=payment_count,
            cash_amount=cash_amount,
            card_amount=card_amount,
            other_amount=other_amount,
            created_by=request.user,
        )
        calc.payments.set(payments)

        return Response({
            'id': calc.id,
            'total_amount': str(total_amount),
            'payment_count': payments.count(),
            'cash_amount': str(cash_amount),
            'card_amount': str(card_amount),
            'other_amount': str(other_amount),
            'detail': 'Hesablama tamamlandı',
        })


class WithdrawnListCustomView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        restaurant = get_user_restaurant(request.user)
        qs = filter_queryset_by_restaurant(
            Statistics.objects.all(), restaurant
        )
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        total = qs.aggregate(total=Sum('withdrawn_amount'))['total'] or 0
        return {'total_withdrawn': str(total), 'count': qs.count()}


class PrinterScanView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.printers.utils.printer_discovery import discover_printers
        printers = discover_printers()
        return Response({'printers': printers})


class ShiftHandoverConfirmView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        from apps.users.models import ShiftHandover
        handover = ShiftHandover.objects.filter(pk=pk).first()
        if not handover:
            return Response({'detail': 'Not found'}, status=404)
        if handover.is_confirmed:
            return Response({'detail': 'Artıq təsdiqlənib'}, status=400)
        if request.user != handover.to_user:
            return Response({'detail': 'Yalnız qəbul edən təsdiqləyə bilər'}, status=403)

        handover.is_confirmed = True
        handover.confirmed_at = timezone.now()
        handover.save()
        return Response({'detail': 'Növbə təhvil-təslimi təsdiqləndi'})
