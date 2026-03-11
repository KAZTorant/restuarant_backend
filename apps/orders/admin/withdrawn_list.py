from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.http import JsonResponse
from django.urls import path
from datetime import timedelta, datetime
from decimal import Decimal

from apps.orders.models import Statistics


class WithdrawnList(Statistics):
    """
    Proxy model for Statistics to create a separate admin view for withdrawn amounts.
    """
    class Meta:
        proxy = True
        verbose_name = "Çıxarılmış Məbləğ"
        verbose_name_plural = "Çıxarılmış Məbləğlər 💰"


class WithdrawnListAdmin(admin.ModelAdmin):
    """
    Admin view to display only withdrawn amounts from closed shifts.
    This creates a dedicated section in the admin panel.
    """
    
    change_list_template = 'admin/orders/withdrawn_list_change_list.html'
    
    # This will make it a read-only view
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    list_display = [
        'shift_id',
        'end_date_formatted',
        'cash_earned_display',
        'card_total_display',
        'other_total_display',
        'extra_initial_cash_display',
        'cash_in_hand_display',
        'withdrawn_amount_display',
        'remaining_cash_display',
        'notes_short',
    ]
    
    list_filter = ['end_time', 'started_by', 'ended_by']
    search_fields = ['withdrawn_notes', 'started_by__username', 'ended_by__username']
    date_hierarchy = 'end_time'
    ordering = ['-end_time']
    
    def get_queryset(self, request):
        """Show all closed shifts"""
        qs = super().get_queryset(request)
        return qs.filter(
            title='till_now',
            is_closed=True,
        ).select_related('started_by', 'ended_by')
    
    def shift_id(self, obj):
        return obj.id
    shift_id.short_description = 'ID'
    
    def end_date_formatted(self, obj):
        if obj.end_time:
            return obj.end_time.strftime('%d.%m.%Y %H:%M')
        return 'N/A'
    end_date_formatted.short_description = 'Bağlanma Tarixi'
    end_date_formatted.admin_order_field = 'end_time'
    
    def started_by_name(self, obj):
        if obj.started_by:
            full_name = f"{obj.started_by.first_name} {obj.started_by.last_name}".strip()
            return full_name if full_name else obj.started_by.username
        return 'N/A'
    started_by_name.short_description = 'Növbəni Açan'
    started_by_name.admin_order_field = 'started_by__username'
    
    def ended_by_name(self, obj):
        if obj.ended_by:
            full_name = f"{obj.ended_by.first_name} {obj.ended_by.last_name}".strip()
            return full_name if full_name else obj.ended_by.username
        return 'N/A'
    ended_by_name.short_description = 'Növbəni Bağlayan'
    ended_by_name.admin_order_field = 'ended_by__username'
    
    def cash_earned_display(self, obj):
        """Display cash earned during the shift (without initial cash)"""
        return format_html(
            '<span style="color: #f0ad4e; font-weight: bold;">{} AZN</span>',
            obj.cash_total
        )
    cash_earned_display.short_description = 'Nağd Qazanılmış'
    cash_earned_display.admin_order_field = 'cash_total'
    
    def card_total_display(self, obj):
        """Display total card payments during the shift"""
        return format_html(
            '<span style="color: #5bc0de; font-weight: bold;">{} AZN</span>',
            obj.card_total
        )
    card_total_display.short_description = 'Kartla Ümumi'
    card_total_display.admin_order_field = 'card_total'
    
    def other_total_display(self, obj):
        """Display total other payments during the shift"""
        return format_html(
            '<span style="color: #9b59b6; font-weight: bold;">{} AZN</span>',
            obj.other_total
        )
    other_total_display.short_description = 'Digər Ödənişlər'
    other_total_display.admin_order_field = 'other_total'
    
    def extra_paid_amount_display(self, obj):
        """Display extra amount paid compared to order totals (tips, overpayment, etc.)"""
        # Calculate total payments
        total_paid = obj.cash_total + obj.card_total + obj.other_total
        # Get order totals (obj.total includes all order amounts)
        order_total = obj.total
        # Calculate the difference
        extra_amount = total_paid - order_total
        
        if extra_amount > 0:
            return format_html(
                '<span style="color: #e67e22; font-weight: bold;">+{} AZN</span>',
                extra_amount
            )
        elif extra_amount < 0:
            return format_html(
                '<span style="color: #e74c3c; font-weight: bold;">{} AZN</span>',
                extra_amount
            )
        else:
            return format_html('<span style="color: #95a5a6;">0.00 AZN</span>')
    
    extra_paid_amount_display.short_description = 'Əlavə Ödənilmiş'
    extra_paid_amount_display.admin_order_field = 'total'
    
    def extra_initial_cash_display(self, obj):
        """Display extra initial cash added at shift start (difference from previous remaining)"""
        # Get the previous shift's remaining cash
        previous_shift = Statistics.objects.filter(
            title='till_now',
            is_closed=True,
            end_time__lt=obj.start_time
        ).order_by('-end_time').first()
        
        if previous_shift:
            expected_initial = previous_shift.remaining_cash
            actual_initial = obj.initial_cash
            extra_amount = actual_initial - expected_initial
            
            if extra_amount > 0:
                return format_html(
                    '<span style="color: #e74c3c; font-weight: bold;">+{} AZN</span>',
                    extra_amount
                )
            elif extra_amount < 0:
                return format_html(
                    '<span style="color: #3498db; font-weight: bold;">{} AZN</span>',
                    extra_amount
                )
            else:
                return format_html('<span style="color: #95a5a6;">0.00 AZN</span>')
        else:
            # First shift, show initial cash
            if obj.initial_cash > 0:
                return format_html(
                    '<span style="color: #e74c3c; font-weight: bold;">+{} AZN</span>',
                    obj.initial_cash
                )
            return format_html('<span style="color: #95a5a6;">0.00 AZN</span>')
    
    extra_initial_cash_display.short_description = 'Kassada Artıq Məbləğ'
    
    def cash_in_hand_display(self, obj):
        cash = obj.cash_total + obj.initial_cash
        return format_html(
            '<span style="color: #5cb85c; font-weight: bold;">{} AZN</span>',
            cash
        )
    cash_in_hand_display.short_description = 'Nağd Ümumi'
    cash_in_hand_display.admin_order_field = 'cash_total'
    
    def withdrawn_amount_display(self, obj):
        return format_html(
            '<span style="color: #d9534f; font-weight: bold;">{} AZN</span>',
            obj.withdrawn_amount
        )
    withdrawn_amount_display.short_description = 'Çıxarılmış Məbləğ'
    withdrawn_amount_display.admin_order_field = 'withdrawn_amount'
    
    def remaining_cash_display(self, obj):
        return format_html(
            '<span style="color: #5cb85c; font-weight: bold;">{} AZN</span>',
            obj.remaining_cash
        )
    remaining_cash_display.short_description = 'Qalan Nağd'
    remaining_cash_display.admin_order_field = 'remaining_cash'
    
    def notes_short(self, obj):
        notes = obj.withdrawn_notes or "-"
        if len(notes) > 50:
            return notes[:47] + "..."
        return notes
    notes_short.short_description = 'Qeyd'
    
    def get_urls(self):
        """Add custom URL for date range calculation"""
        urls = super().get_urls()
        custom_urls = [
            path('calculate-total/', 
                 self.admin_site.admin_view(self.calculate_total_view),
                 name='withdrawn_calculate_total'),
        ]
        return custom_urls + urls
    
    def calculate_total_view(self, request):
        """Calculate total withdrawn amount for a date range"""
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Başlanğıc və bitmə tarixləri tələb olunur'
            })
        
        try:
            # Parse dates
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # Make them timezone aware for filtering
            start_datetime = timezone.make_aware(
                datetime.combine(start_date, datetime.min.time())
            )
            end_datetime = timezone.make_aware(
                datetime.combine(end_date, datetime.max.time())
            )
            
            # Get all closed shifts in date range
            shifts = Statistics.objects.filter(
                title='till_now',
                is_closed=True,
                end_time__gte=start_datetime,
                end_time__lte=end_datetime
            )
            
            # Get payments directly from Payment model for accurate amounts (includes tips/extra)
            from apps.payments.models import Payment
            
            payments = Payment.objects.filter(
                paid_at__gte=start_datetime,
                paid_at__lte=end_datetime
            )
            
            # Calculate totals from actual payment amounts
            total_cash_earned = Decimal('0.00')
            total_card = Decimal('0.00')
            total_other = Decimal('0.00')
            
            for payment in payments:
                if payment.payment_methods.exists():
                    # Multiple payment methods
                    for method in payment.payment_methods.all():
                        if method.payment_type == 'cash':
                            total_cash_earned += method.amount
                        elif method.payment_type == 'card':
                            total_card += method.amount
                        else:
                            total_other += method.amount
                else:
                    # Single payment method
                    if payment.payment_type == 'cash':
                        total_cash_earned += payment.paid_amount
                    elif payment.payment_type == 'card':
                        total_card += payment.paid_amount
                    else:
                        total_other += payment.paid_amount
            
            # Calculate totals from shifts
            total_withdrawn = sum(shift.withdrawn_amount for shift in shifts)
            total_withdrawn_card = sum(shift.withdrawn_from_card for shift in shifts)
            total_withdrawn_other = sum(shift.withdrawn_from_other for shift in shifts)
            
            # Calculate total extra initial amounts for each payment type
            total_extra_initial_cash = Decimal('0.00')
            total_extra_initial_card = Decimal('0.00')
            total_extra_initial_other = Decimal('0.00')
            
            shifts_list = list(shifts.order_by('start_time'))
            for i, shift in enumerate(shifts_list):
                if i > 0:
                    # Compare with previous shift
                    prev_shift = shifts_list[i-1]
                    extra_cash = shift.initial_cash - prev_shift.remaining_cash
                    extra_card = shift.initial_card - prev_shift.remaining_card
                    extra_other = shift.initial_other - prev_shift.remaining_other
                    total_extra_initial_cash += extra_cash
                    total_extra_initial_card += extra_card
                    total_extra_initial_other += extra_other
                else:
                    # First shift in range, add its initial amounts if they're extra
                    first_before = Statistics.objects.filter(
                        title='till_now',
                        is_closed=True,
                        end_time__lt=shift.start_time
                    ).order_by('-end_time').first()
                    if first_before:
                        total_extra_initial_cash += shift.initial_cash - first_before.remaining_cash
                        total_extra_initial_card += shift.initial_card - first_before.remaining_card
                        total_extra_initial_other += shift.initial_other - first_before.remaining_other
                    else:
                        total_extra_initial_cash += shift.initial_cash
                        total_extra_initial_card += shift.initial_card
                        total_extra_initial_other += shift.initial_other
            
            # Ümumi Alvər = All earned + All extra initials
            total_sales = (total_cash_earned + total_card + total_other + 
                          total_extra_initial_cash + total_extra_initial_card + total_extra_initial_other)
            
            # Ümumi amounts = Earned + Extra Initial
            total_cash = total_cash_earned + total_extra_initial_cash
            total_card_with_initial = total_card + total_extra_initial_card
            total_other_with_initial = total_other + total_extra_initial_other
            
            # Qalan amounts = Total - Withdrawn
            total_remaining_cash = total_cash - total_withdrawn
            total_remaining_card = total_card_with_initial - total_withdrawn_card
            total_remaining_other = total_other_with_initial - total_withdrawn_other
            
            count = shifts.count()
            
            return JsonResponse({
                'success': True,
                'start_date': start_date.strftime('%d.%m.%Y'),
                'end_date': end_date.strftime('%d.%m.%Y'),
                'count': count,
                'total_withdrawn': str(total_withdrawn),
                'total_withdrawn_card': str(total_withdrawn_card),
                'total_withdrawn_other': str(total_withdrawn_other),
                'total_cash': str(total_cash),
                'total_cash_earned': str(total_cash_earned),
                'total_card': str(total_card),
                'total_card_with_initial': str(total_card_with_initial),
                'total_other': str(total_other),
                'total_other_with_initial': str(total_other_with_initial),
                'total_extra_initial_cash': str(total_extra_initial_cash),
                'total_extra_initial_card': str(total_extra_initial_card),
                'total_extra_initial_other': str(total_extra_initial_other),
                'total_sales': str(total_sales),
                'total_remaining_cash': str(total_remaining_cash),
                'total_remaining_card': str(total_remaining_card),
                'total_remaining_other': str(total_remaining_other),
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Tarix formatı səhvdir: {str(e)}'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Xəta baş verdi: {str(e)}'
            })


# Register the proxy model
admin.site.register(WithdrawnList, WithdrawnListAdmin)

