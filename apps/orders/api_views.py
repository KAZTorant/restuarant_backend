from decimal import Decimal

from django.db.models import Sum
from django.http import JsonResponse

from apps.orders.models import Order
from apps.payments.models import Payment


def active_orders_api(request):
    """
    API endpoint to get payment amounts by type and unpaid amounts
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get all paid orders that are not deleted
        paid_orders = Order.objects.filter(
            is_paid=True,
            is_deleted=False
        )
        
        # Get all unpaid orders that are not deleted
        unpaid_orders = Order.objects.filter(
            is_paid=False,
            is_deleted=False
        )
        
        # Get all payments linked to paid orders
        all_payments = Payment.objects.filter(orders__in=paid_orders).distinct()
        
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
                    if method.payment_type == Payment.PaymentType.CASH and change_amount > 0:
                        method_amount = method_amount - change_amount
                        change_amount = Decimal('0.00')  # Only subtract once
                    
                    if method.payment_type == Payment.PaymentType.CASH:
                        cash_total += method_amount
                    elif method.payment_type == Payment.PaymentType.CARD:
                        card_total += method_amount
                    elif method.payment_type == Payment.PaymentType.OTHER:
                        other_total += method_amount
            else:
                # Fallback to old payment_type field
                if payment.payment_type == Payment.PaymentType.CASH:
                    cash_total += payment.final_price
                elif payment.payment_type == Payment.PaymentType.CARD:
                    card_total += payment.final_price
                elif payment.payment_type == Payment.PaymentType.OTHER:
                    other_total += payment.final_price
        
        # Calculate unpaid total
        unpaid_total = unpaid_orders.aggregate(
            total=Sum('total_price')
        )['total'] or Decimal('0.00')
        
        return JsonResponse({
            'cash_total': float(cash_total),
            'card_total': float(card_total),
            'other_total': float(other_total),
            'unpaid_total': float(unpaid_total)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)