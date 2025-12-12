#!/usr/bin/env python3

import os
import sys
from datetime import date, datetime, time
from decimal import Decimal

import django

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

from apps.payments.models import Payment, PaymentCalculation, PaymentMethod
from apps.tables.models import Table

User = get_user_model()

def test_payment_calculation():
    print("🧮 Testing Payment Calculation Functionality...")
    
    # Get or create a test user
    test_user, created = User.objects.get_or_create(
        username='test_operator',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    if created:
        test_user.set_password('test123')
        test_user.save()
        print(f"✅ Created test user: {test_user.username}")
    else:
        print(f"✅ Using existing test user: {test_user.username}")
    
    # Get existing payments count
    existing_payments = Payment.objects.count()
    print(f"📊 Found {existing_payments} existing payments in database")
    
    if existing_payments > 0:
        # Test with a broad date range to include all payments
        start_date = date(2025, 12, 10)
        end_date = date(2025, 12, 10)
        start_time = time(0, 0)  # 00:00
        end_time = time(23, 59)  # 23:59
        
        # Simulate the calculation process
        start_datetime = datetime.combine(start_date, start_time)
        end_datetime = datetime.combine(end_date, end_time)
        
        # Make timezone aware
        from django.utils import timezone
        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
        if timezone.is_naive(end_datetime):
            end_datetime = timezone.make_aware(end_datetime)
        
        # Filter payments by datetime range
        payments = Payment.objects.filter(
            paid_at__gte=start_datetime,
            paid_at__lte=end_datetime
        )
        
        print(f"📅 Payments in range {start_date} {start_time} - {end_date} {end_time}: {payments.count()}")
        
        if payments.exists():
            # Calculate totals
            total_amount = sum(payment.final_price for payment in payments)
            payment_count = payments.count()
            
            # Calculate amounts by payment type
            cash_amount = Decimal('0')
            card_amount = Decimal('0')
            other_amount = Decimal('0')
            
            for payment in payments:
                if payment.payment_methods.exists():
                    # If payment has multiple payment methods
                    for method in payment.payment_methods.all():
                        if method.payment_type == 'cash':
                            cash_amount += method.amount
                        elif method.payment_type == 'card':
                            card_amount += method.amount
                        else:
                            other_amount += method.amount
                else:
                    # If payment has only one payment type
                    if payment.payment_type == 'cash':
                        cash_amount += payment.paid_amount
                    elif payment.payment_type == 'card':
                        card_amount += payment.paid_amount
                    else:
                        other_amount += payment.paid_amount
            
            print(f"💰 Total Amount: {total_amount}₼")
            print(f"🧾 Payment Count: {payment_count}")
            print(f"💵 Cash Amount: {cash_amount}₼")
            print(f"💳 Card Amount: {card_amount}₼")
            print(f"🔄 Other Amount: {other_amount}₼")
            
            # Create calculation record
            calculation = PaymentCalculation.objects.create(
                start_date=start_date,
                end_date=end_date,
                start_time=start_time,
                end_time=end_time,
                total_amount=total_amount,
                payment_count=payment_count,
                cash_amount=cash_amount,
                card_amount=card_amount,
                other_amount=other_amount,
                created_by=test_user
            )
            
            print(f"✅ Calculation saved with ID: {calculation.id}")
            print(f"📈 Calculation Details:")
            print(f"   - Date Range: {calculation.date_range_display}")
            print(f"   - Time Range: {calculation.time_range_display}")
            print(f"   - Created By: {calculation.created_by.username}")
            print(f"   - Created At: {calculation.created_at}")
            
        else:
            print("⚠️  No payments found in the specified date range")
    else:
        print("⚠️  No payments found in database to test calculation")
    
    # Check if all PaymentCalculation records
    all_calculations = PaymentCalculation.objects.all().order_by('-created_at')
    print(f"\n📋 Total Payment Calculations: {all_calculations.count()}")
    
    for calc in all_calculations[:3]:  # Show last 3 calculations
        print(f"   📊 ID {calc.id}: {calc.date_range_display} | {calc.total_amount}₼ | {calc.payment_count} payments")

if __name__ == '__main__':
    test_payment_calculation()
