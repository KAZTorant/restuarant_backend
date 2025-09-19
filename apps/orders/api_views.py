from datetime import datetime
from decimal import Decimal

from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.orders.models import Order, Statistics
from apps.payments.models import Payment


def active_orders_api(request):
    """
    API endpoint to get payment amounts by type and unpaid amounts

    Query parameters:
    - start_date: ISO format datetime string (e.g., '2025-09-10T00:00:00')
    - end_date: ISO format datetime string (e.g., '2025-09-10T23:59:59')
    - date: ISO format date string (e.g., '2025-09-10') - shortcut for filtering by specific date
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Parse datetime filters from query parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        date_filter = request.GET.get('date')

        # Build base queryset
        orders_queryset = Order.objects.filter(is_deleted=False)

        # Apply datetime filtering
        if date_filter:
            # If date is provided, filter for that specific date (00:00:00 to 23:59:59)
            try:
                filter_date = datetime.fromisoformat(date_filter).date()
                start_of_day = timezone.make_aware(
                    datetime.combine(filter_date, datetime.min.time()))
                end_of_day = timezone.make_aware(
                    datetime.combine(filter_date, datetime.max.time()))
                orders_queryset = orders_queryset.filter(
                    created_at__gte=start_of_day,
                    created_at__lte=end_of_day
                )
            except ValueError:
                return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD format.'}, status=400)
        else:
            # Apply start_date and end_date filters if provided
            if start_date:
                try:
                    start_datetime = parse_datetime(start_date)
                    if start_datetime is None:
                        start_datetime = timezone.make_aware(
                            datetime.fromisoformat(start_date))
                    orders_queryset = orders_queryset.filter(
                        created_at__gte=start_datetime)
                except (ValueError, TypeError):
                    return JsonResponse({'error': 'Invalid start_date format. Use ISO format: YYYY-MM-DDTHH:MM:SS'}, status=400)

            if end_date:
                try:
                    end_datetime = parse_datetime(end_date)
                    if end_datetime is None:
                        end_datetime = timezone.make_aware(
                            datetime.fromisoformat(end_date))
                    orders_queryset = orders_queryset.filter(
                        created_at__lte=end_datetime)
                except (ValueError, TypeError):
                    return JsonResponse({'error': 'Invalid end_date format. Use ISO format: YYYY-MM-DDTHH:MM:SS'}, status=400)

        # Get all paid orders that are not deleted (with datetime filter applied)
        paid_orders = orders_queryset.filter(is_paid=True)

        # Get all unpaid orders that are not deleted (with datetime filter applied)
        unpaid_orders = orders_queryset.filter(is_paid=False)

        # Get all payments linked to paid orders
        all_payments = Payment.objects.filter(
            orders__in=paid_orders).distinct()

        # Initialize totals
        cash_total = Decimal('0.00')
        card_total = Decimal('0.00')
        other_total = Decimal('0.00')

        # Process each payment (same logic as your Statistics model)
        for payment in all_payments:
            if payment.payment_methods.exists():
                # Use the new payment methods
                change_amount = payment.change or Decimal('0.00')

                for method in payment.payment_methods.all():
                    method_amount = method.amount

                    # If this is cash and there's change, subtract the change from cash
                    if method.payment_type == 'cash' and change_amount > 0:
                        method_amount = method_amount - change_amount
                        change_amount = Decimal('0.00')  # Only subtract once

                    if method.payment_type == 'cash':
                        cash_total += method_amount
                    elif method.payment_type == 'card':
                        card_total += method_amount
                    elif method.payment_type == 'other':
                        other_total += method_amount
            else:
                # Fallback to old payment_type field
                if payment.payment_type == 'cash':
                    cash_total += payment.final_price
                elif payment.payment_type == 'card':
                    card_total += payment.final_price
                elif payment.payment_type == 'other':
                    other_total += payment.final_price

        # Calculate unpaid total
        unpaid_total = unpaid_orders.aggregate(
            total=Sum('total_price')
        )['total'] or Decimal('0.00')

        return JsonResponse({
            'cash_total': float(cash_total),
            'card_total': float(card_total),
            'other_total': float(other_total),
            'unpaid_total': float(unpaid_total),
            'paid_total': float(cash_total + card_total + other_total),
            'filters_applied': {
                'start_date': start_date,
                'end_date': end_date,
                'date': date_filter
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def daily_report_api(request):
    """
    API endpoint to get payment amounts since last closed report (daily report)

    This endpoint finds the last closed statistics report and returns order data
    from that report's end_time until now.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Find the last closed report
        last_report = Statistics.objects.filter(
            is_closed=True).order_by('-end_time').first()

        if not last_report or not last_report.end_time:
            # If no closed report exists, calculate ALL orders (from beginning of time)
            start_datetime = None  # No start date limit
            end_datetime = timezone.now()
            last_report_end_time = None
            last_report_ended_by = None
        else:
            # Use last report's end time as start date, current time as end date
            start_datetime = last_report.end_time
            end_datetime = timezone.now()
            last_report_end_time = last_report.end_time.isoformat()
            last_report_ended_by = last_report.ended_by.username if last_report.ended_by else 'Unknown'

        # Build queryset with date range
        if start_datetime:
            # If there's a closed report, get orders after that report
            orders_queryset = Order.objects.filter(
                is_deleted=False,
                created_at__gte=start_datetime,
                created_at__lte=end_datetime
            )
        else:
            # If no closed report, get ALL orders (from beginning of time)
            orders_queryset = Order.objects.filter(
                is_deleted=False,
                created_at__lte=end_datetime
            )

        # Get all paid orders in this range
        paid_orders = orders_queryset.filter(is_paid=True)

        # Get all unpaid orders in this range
        unpaid_orders = orders_queryset.filter(is_paid=False)

        # Get all payments linked to paid orders
        all_payments = Payment.objects.filter(
            orders__in=paid_orders).distinct()

        # Initialize totals
        cash_total = Decimal('0.00')
        card_total = Decimal('0.00')
        other_total = Decimal('0.00')

        # Process each payment (same logic as active_orders_api)
        for payment in all_payments:
            if payment.payment_methods.exists():
                # Use the new payment methods
                change_amount = payment.change or Decimal('0.00')

                for method in payment.payment_methods.all():
                    method_amount = method.amount

                    # If this is cash and there's change, subtract the change from cash
                    if method.payment_type == 'cash' and change_amount > 0:
                        method_amount = method_amount - change_amount
                        change_amount = Decimal('0.00')  # Only subtract once

                    if method.payment_type == 'cash':
                        cash_total += method_amount
                    elif method.payment_type == 'card':
                        card_total += method_amount
                    elif method.payment_type == 'other':
                        other_total += method_amount
            else:
                # Fallback to old payment_type field
                if payment.payment_type == 'cash':
                    cash_total += payment.final_price
                elif payment.payment_type == 'card':
                    card_total += payment.final_price
                elif payment.payment_type == 'other':
                    other_total += payment.final_price

        # Calculate unpaid total
        unpaid_total = unpaid_orders.aggregate(
            total=Sum('total_price')
        )['total'] or Decimal('0.00')

        return JsonResponse({
            'cash_total': float(cash_total),
            'card_total': float(card_total),
            'other_total': float(other_total),
            'unpaid_total': float(unpaid_total),
            'paid_total': float(cash_total + card_total + other_total),
            'last_report_end_time': last_report_end_time,
            'current_time': end_datetime.isoformat(),
            'last_report_ended_by': last_report_ended_by
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
