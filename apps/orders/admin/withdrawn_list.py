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
        'started_by_name',
        'ended_by_name',
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
        """Only show closed shifts with withdrawn amounts"""
        qs = super().get_queryset(request)
        return qs.filter(
            title='till_now',
            is_closed=True,
        ).exclude(
            withdrawn_amount=0
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
            
            # Get withdrawn shifts in date range
            shifts = Statistics.objects.filter(
                title='till_now',
                is_closed=True,
                end_time__gte=start_datetime,
                end_time__lte=end_datetime
            ).exclude(withdrawn_amount=0)
            
            # Calculate totals
            total_withdrawn = sum(shift.withdrawn_amount for shift in shifts)
            total_cash = sum(shift.cash_total + shift.initial_cash for shift in shifts)
            total_remaining = sum(shift.remaining_cash for shift in shifts)
            count = shifts.count()
            
            return JsonResponse({
                'success': True,
                'start_date': start_date.strftime('%d.%m.%Y'),
                'end_date': end_date.strftime('%d.%m.%Y'),
                'count': count,
                'total_withdrawn': str(total_withdrawn),
                'total_cash': str(total_cash),
                'total_remaining': str(total_remaining),
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

