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
    API endpoint to get payment amounts by type and unpaid amounts using Report model

    Query parameters:
    - start_date: ISO format datetime string (e.g., '2025-09-10T00:00:00')
    - end_date: ISO format datetime string (e.g., '2025-09-10T23:59:59')
    - date: ISO format date string (e.g., '2025-09-10') - shortcut for filtering by specific date
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        from datetime import datetime, timedelta
        from apps.orders.models import Report

        # Parse datetime filters from query parameters
        start_date_param = request.GET.get('start_date')
        end_date_param = request.GET.get('end_date')
        date_filter = request.GET.get('date')

        # Determine date range to process
        if date_filter:
            # Single date - create report for that date
            try:
                target_date = datetime.fromisoformat(date_filter).date()
                start_date = target_date
                end_date = target_date
            except ValueError:
                return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD format.'}, status=400)
        else:
            # Date range - parse start and end dates
            if not start_date_param or not end_date_param:
                return JsonResponse({'error': 'Both start_date and end_date are required for date range queries'}, status=400)

            try:
                start_datetime = parse_datetime(start_date_param)
                if start_datetime is None:
                    start_datetime = timezone.make_aware(
                        datetime.fromisoformat(start_date_param))
                start_date = start_datetime.date()

                end_datetime = parse_datetime(end_date_param)
                if end_datetime is None:
                    end_datetime = timezone.make_aware(
                        datetime.fromisoformat(end_date_param))
                end_date = end_datetime.date()
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Invalid date format. Use ISO format: YYYY-MM-DDTHH:MM:SS'}, status=400)

        # Initialize aggregate totals
        total_cash = Decimal('0.00')
        total_card = Decimal('0.00')
        total_other = Decimal('0.00')
        total_unpaid = Decimal('0.00')

        # Generate reports for each date in the range
        current_date = start_date
        while current_date <= end_date:
            # Get or create report for this date
            report, created = Report.objects.get_or_create_for_date(
                current_date)

            # Update totals to ensure current data
            report.update_totals()

            # Add to aggregate totals
            total_cash += report.cash_total
            total_card += report.card_total
            total_other += report.other_total
            total_unpaid += report.unpaid_total

            # Move to next date
            current_date += timedelta(days=1)

        # Calculate paid total
        paid_total = total_cash + total_card + total_other

        return JsonResponse({
            'cash_total': float(total_cash),
            'card_total': float(total_card),
            'other_total': float(total_other),
            'unpaid_total': float(total_unpaid),
            'paid_total': float(paid_total),
            'filters_applied': {
                'start_date': start_date_param,
                'end_date': end_date_param,
                'date': date_filter
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def period_report_api(request):
    """
    API endpoint to get period report for specific date using Report model
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        from datetime import datetime
        from apps.orders.models import Report

        # Get date parameter
        date_str = request.GET.get('date')
        if not date_str:
            return JsonResponse({'error': 'Date parameter required'}, status=400)

        # Parse date
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

        # Get or create report for this date
        report, created = Report.objects.get_or_create_for_date(date_obj)

        # Update totals to ensure current data
        report.update_totals()

        # Calculate paid total
        paid_total = float(report.cash_total +
                           report.card_total + report.other_total)

        return JsonResponse({
            'cash_total': float(report.cash_total),
            'card_total': float(report.card_total),
            'other_total': float(report.other_total),
            'unpaid_total': float(report.unpaid_total),
            'paid_total': paid_total,
            'total_amount': float(report.total_amount),
            'period_start': report.start_datetime.isoformat(),
            'period_end': report.end_datetime.isoformat(),
            'period_name': report.work_period_config.name,
            'date': date_str
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
