from datetime import date, datetime, time

from django import forms
from django.contrib import admin, messages
from django.db.models import Q, Sum
from django.forms import DateField, ModelForm, TimeField
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from apps.payments.models import Payment, PaymentCalculation


class PaymentCalculationForm(forms.Form):
    start_date = forms.DateField(
        label=_("Başlanğıc tarixi"),
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=date.today()
    )
    end_date = forms.DateField(
        label=_("Son tarixi"),
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=date.today()
    )
    start_time = forms.CharField(
        label=_("Başlanğıc saatı (SS:DD)"),
        max_length=5,
        widget=forms.TextInput(attrs={
            'placeholder': '12:00',
            'pattern': '[0-2][0-9]:[0-5][0-9]',
            'title': '24 saat formatı (SS:DD)',
            'class': 'time-input-24h',
            'value': '12:00'
        }),
        initial='12:00'
    )
    end_time = forms.CharField(
        label=_("Son saatı (SS:DD)"),
        max_length=5,
        widget=forms.TextInput(attrs={
            'placeholder': '23:59',
            'pattern': '[0-2][0-9]:[0-5][0-9]',
            'title': '24 saat formatı (SS:DD)',
            'class': 'time-input-24h',
            'value': '23:59'
        }),
        initial='23:59'
    )

    def clean_start_time(self):
        time_str = self.cleaned_data.get('start_time')
        if not time_str:
            return time(12, 0)
        
        try:
            hours, minutes = map(int, time_str.split(':'))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return time(hours, minutes)
            raise forms.ValidationError(_('Yanlış saat formatı. 00:00-23:59 arasında olmalıdır'))
        except (ValueError, AttributeError):
            raise forms.ValidationError(_('Yanlış saat formatı. SS:DD formatında daxil edin (məsələn: 14:30)'))

    def clean_end_time(self):
        time_str = self.cleaned_data.get('end_time')
        if not time_str:
            return time(23, 59)
        
        try:
            hours, minutes = map(int, time_str.split(':'))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return time(hours, minutes)
            raise forms.ValidationError(_('Yanlış saat formatı. 00:00-23:59 arasında olmalıdır'))
        except (ValueError, AttributeError):
            raise forms.ValidationError(_('Yanlış saat formatı. SS:DD formatında daxil edin (məsələn: 14:30)'))


@admin.register(PaymentCalculation)
class PaymentCalculationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'date_range_display',
        'time_range_display',
        'total_amount',
        'total_paid_display',
        'payment_count',
        'cash_amount_detailed',
        'card_amount_detailed',
        'other_amount_detailed',
        'extra_paid_amount_display',
        'created_by',
        'created_at',
        'print_button',
    )
    list_filter = (
        'start_date',
        'end_date',
        'created_by',
        'created_at',
    )

    list_per_page = 1

    search_fields = (
        'created_by__username',
    )
    readonly_fields = (
        'total_amount',
        'payment_count',
        'cash_amount',
        'card_amount',
        'other_amount',
        'extra_paid_amount_display',
        'created_by',
        'created_at',
        'date_range_display',
        'time_range_display',
        'payments_display',
        'product_sales_display',
        'waiter_payments_display',
    )

    fieldsets = (
        (_('Tarix və vaxt məlumatları'), {
            'fields': (
                'date_range_display',
                'time_range_display',
            )
        }),
        (_('Ödəniş məlumatları'), {
            'fields': (
                'payment_count',
                'total_amount',
                'cash_amount',
                'card_amount',
                'other_amount',
                'extra_paid_amount_display',
            )
        }),
        (_('Yaradılma məlumatları'), {
            'fields': (
                'created_by',
                'created_at',
            )
        }),
        (_('Ofisiantlar üzrə ödənişlər'), {
            'fields': ('waiter_payments_display',),
        }),
        (_('Ödənişlər'), {
            'fields': ('payments_display',),
            'classes': ('collapse',),
        }),
        (_('Satılan məhsullar'), {
            'fields': ('product_sales_display',),
        }),
    )

    def payments_display(self, obj):
        if not obj.pk:
            return "-"
        
        payments = obj.get_payments()
        
        if not payments.exists():
            return _("Ödəniş yoxdur")
        
        rows = []
        for payment in payments:
            # Get payment methods
            payment_methods = []
            if payment.payment_methods.exists():
                for method in payment.payment_methods.all():
                    payment_methods.append(
                        f"{method.get_payment_type_display()}: {method.amount}₼"
                    )
            else:
                payment_methods.append(
                    f"{payment.get_payment_type_display()}: {payment.paid_amount}₼"
                )
            
            # Get orders for this payment
            orders_info = []
            for order in payment.orders.all():
                orders_info.append(f"Sifariş #{order.id}")
            
            # Convert to local timezone
            from django.utils.timezone import localtime
            local_paid_at = localtime(payment.paid_at)
            
            rows.append(f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{payment.id}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{payment.table.number}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{', '.join(orders_info)}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{payment.final_price}₼</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{', '.join(payment_methods)}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{payment.paid_by.username if payment.paid_by else '-'}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{local_paid_at.strftime('%d.%m.%Y %H:%M')}</td>
                </tr>
            """)
        
        html = f"""
        <div style="margin: 20px 0;">
            <h3>Cəmi {payments.count()} ödəniş</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">ID</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Masa</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Sifarişlər</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Məbləğ</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Ödəniş növü</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Operator</th>
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Tarix</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
        return mark_safe(html)
    
    payments_display.short_description = _("Ödənişlər")

    def product_sales_display(self, obj):
        if not obj.pk:
            return "-"
        
        products = obj.get_product_sales_summary()
        
        if not products:
            return _("Məhsul satışı yoxdur")
        
        rows = []
        total_quantity = 0
        total_amount = 0
        
        for product in products:
            total_quantity += product['quantity']
            total_amount += product['total']
            rows.append(f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{product['name']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{product['quantity']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{product['total']:.2f}₼</td>
                </tr>
            """)
        
        # Add total row
        rows.append(f"""
            <tr style="background-color: #e8f4f8; font-weight: bold;">
                <td style="padding: 8px; border: 1px solid #ddd;">CƏMI</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{total_quantity}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_amount:.2f}₼</td>
            </tr>
        """)
        
        html = f"""
        <div style="margin: 20px 0;">
            <h3>Satılan məhsullar ({len(products)} növ məhsul)</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Məhsul adı</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Miqdar</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Cəmi məbləğ</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
        return mark_safe(html)
    
    product_sales_display.short_description = _("Satılan məhsullar")

    def waiter_payments_display(self, obj):
        """Display payment summary grouped by waiter"""
        if not obj.pk:
            return "-"
        
        waiters = obj.get_waiter_payments_summary()
        
        if not waiters:
            return _("Ofisiant məlumatı yoxdur")
        
        rows = []
        total_amount = 0
        total_payment_count = 0
        total_order_count = 0
        total_cash = 0
        total_card = 0
        total_other = 0
        
        for waiter in waiters:
            total_amount += float(waiter['total_amount'])
            total_payment_count += waiter['payment_count']
            total_order_count += waiter['order_count']
            total_cash += float(waiter['cash_amount'])
            total_card += float(waiter['card_amount'])
            total_other += float(waiter['other_amount'])
            
            rows.append(f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{waiter['waiter_name']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{waiter['order_count']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{waiter['payment_count']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-weight: bold;">{waiter['total_amount']:.2f}₼</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{waiter['cash_amount']:.2f}₼</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{waiter['card_amount']:.2f}₼</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{waiter['other_amount']:.2f}₼</td>
                </tr>
            """)
        
        # Add total row
        rows.append(f"""
            <tr style="background-color: #e8f4f8; font-weight: bold;">
                <td style="padding: 8px; border: 1px solid #ddd;">CƏMI</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{total_order_count}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{total_payment_count}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_amount:.2f}₼</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_cash:.2f}₼</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_card:.2f}₼</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{total_other:.2f}₼</td>
            </tr>
        """)
        
        html = f"""
        <div style="margin: 20px 0;">
            <h3>Ofisiantlar üzrə ödənişlər ({len(waiters)} ofisiant)</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Ofisiant</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Sifariş sayı</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Ödəniş sayı</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Ümumi məbləğ</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Nağd</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Kart</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Digər</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
        return mark_safe(html)
    
    waiter_payments_display.short_description = _("Ofisiantlar üzrə ödənişlər")

    def cash_amount_with_info(self, obj):
        """Display cash amount with an informational tooltip"""
        return format_html(
            '{} ₼ <span title="Yalnız seçilmiş tarix/saat aralığındakı nağd ödənişlər. '
            'Əvvəlki növbə qalıqları daxil deyil." '
            'style="cursor: help; color: #17a2b8; font-weight: bold;">ⓘ</span>',
            obj.cash_amount
        )
    
    cash_amount_with_info.short_description = _("Nağd məbləğ")
    cash_amount_with_info.admin_order_field = 'cash_amount'
    
    def total_paid_display(self, obj):
        """Display total amount paid (cash + card + other)"""
        total_paid = obj.cash_amount + obj.card_amount + obj.other_amount
        return format_html(
            '<span style="color: #2ecc71; font-weight: bold;">{} ₼</span>',
            total_paid
        )
    
    total_paid_display.short_description = _("Ödənilmiş Cəmi")
    total_paid_display.admin_order_field = 'cash_amount'
    
    def cash_amount_detailed(self, obj):
        """Display cash amount with breakdown (base + tip)"""
        # Calculate actual extra amounts per payment type from individual payments
        payments = obj.get_payments()
        
        cash_base = 0
        cash_extra = 0
        
        for payment in payments:
            # Calculate extra for this payment
            payment_extra = payment.paid_amount - payment.final_price
            
            if payment.payment_methods.exists():
                # Multiple payment methods - distribute extra proportionally
                total_paid = sum(m.amount for m in payment.payment_methods.all())
                
                for method in payment.payment_methods.all():
                    if method.payment_type == 'cash':
                        # This method's share of the order
                        method_ratio = method.amount / total_paid if total_paid > 0 else 0
                        method_base = payment.final_price * method_ratio
                        method_extra = payment_extra * method_ratio
                        
                        cash_base += method_base
                        cash_extra += method_extra
            else:
                # Single payment method
                if payment.payment_type == 'cash':
                    cash_base += payment.final_price
                    cash_extra += payment_extra
        
        if cash_extra > 0.01:  # Show breakdown only if there's meaningful extra
            # Format numbers first
            total_str = f"{obj.cash_amount:.2f}"
            base_str = f"{cash_base:.2f}"
            extra_str = f"{cash_extra:.2f}"
            
            return format_html(
                '<span style="font-weight: bold;">{} ₼</span><br>'
                '<span style="font-size: 10px; color: #777;">'
                '({} + <span style="color: #e67e22;">{}</span> Əlavə Ödənilmiş)'
                '</span>',
                total_str, base_str, extra_str
            )
        else:
            return format_html(
                '<span style="font-weight: bold;">{} ₼</span>',
                obj.cash_amount
            )
    
    cash_amount_detailed.short_description = _("Nağd məbləğ")
    cash_amount_detailed.admin_order_field = 'cash_amount'
    
    def card_amount_detailed(self, obj):
        """Display card amount with breakdown (base + tip)"""
        # Calculate actual extra amounts per payment type from individual payments
        payments = obj.get_payments()
        
        card_base = 0
        card_extra = 0
        
        for payment in payments:
            # Calculate extra for this payment
            payment_extra = payment.paid_amount - payment.final_price
            
            if payment.payment_methods.exists():
                # Multiple payment methods - distribute extra proportionally
                total_paid = sum(m.amount for m in payment.payment_methods.all())
                
                for method in payment.payment_methods.all():
                    if method.payment_type == 'card':
                        # This method's share of the order
                        method_ratio = method.amount / total_paid if total_paid > 0 else 0
                        method_base = payment.final_price * method_ratio
                        method_extra = payment_extra * method_ratio
                        
                        card_base += method_base
                        card_extra += method_extra
            else:
                # Single payment method
                if payment.payment_type == 'card':
                    card_base += payment.final_price
                    card_extra += payment_extra
        
        if card_extra > 0.01:  # Show breakdown only if there's meaningful extra
            # Format numbers first
            total_str = f"{obj.card_amount:.2f}"
            base_str = f"{card_base:.2f}"
            extra_str = f"{card_extra:.2f}"
            
            return format_html(
                '<span style="font-weight: bold;">{} ₼</span><br>'
                '<span style="font-size: 10px; color: #777;">'
                '({} + <span style="color: #e67e22;">{}</span> Əlavə Ödənilmiş)'
                '</span>',
                total_str, base_str, extra_str
            )
        else:
            return format_html(
                '<span style="font-weight: bold;">{} ₼</span>',
                obj.card_amount
            )
    
    card_amount_detailed.short_description = _("Kart məbləğ")
    card_amount_detailed.admin_order_field = 'card_amount'
    
    def other_amount_detailed(self, obj):
        """Display other amount with breakdown (base + tip)"""
        # Calculate actual extra amounts per payment type from individual payments
        payments = obj.get_payments()
        
        other_base = 0
        other_extra = 0
        
        for payment in payments:
            # Calculate extra for this payment
            payment_extra = payment.paid_amount - payment.final_price
            
            if payment.payment_methods.exists():
                # Multiple payment methods - distribute extra proportionally
                total_paid = sum(m.amount for m in payment.payment_methods.all())
                
                for method in payment.payment_methods.all():
                    if method.payment_type == 'other':
                        # This method's share of the order
                        method_ratio = method.amount / total_paid if total_paid > 0 else 0
                        method_base = payment.final_price * method_ratio
                        method_extra = payment_extra * method_ratio
                        
                        other_base += method_base
                        other_extra += method_extra
            else:
                # Single payment method
                if payment.payment_type == 'other':
                    other_base += payment.final_price
                    other_extra += payment_extra
        
        if other_extra > 0.01:  # Show breakdown only if there's meaningful extra
            # Format numbers first
            total_str = f"{obj.other_amount:.2f}"
            base_str = f"{other_base:.2f}"
            extra_str = f"{other_extra:.2f}"
            
            return format_html(
                '<span style="font-weight: bold;">{} ₼</span><br>'
                '<span style="font-size: 10px; color: #777;">'
                '({} + <span style="color: #e67e22;">{}</span> Əlavə Ödənilmiş)'
                '</span>',
                total_str, base_str, extra_str
            )
        else:
            return format_html(
                '<span style="font-weight: bold;">{} ₼</span>',
                obj.other_amount
            )
    
    other_amount_detailed.short_description = _("Digər məbləğ")
    other_amount_detailed.admin_order_field = 'other_amount'
    
    def extra_paid_amount_display(self, obj):
        """Display extra amount paid (tips, overpayment, etc.)"""
        extra_amount = obj.extra_paid_amount
        
        if extra_amount > 0:
            return format_html(
                '<span style="color: #e67e22; font-weight: bold;">+{} ₼</span> '
                '<span title="Əlavə ödənilmiş məbləğ (bahşiş, dəyişiklik və s.)" '
                'style="cursor: help; color: #17a2b8; font-size: 12px;">ⓘ</span>',
                extra_amount
            )
        elif extra_amount < 0:
            return format_html(
                '<span style="color: #e74c3c; font-weight: bold;">{} ₼</span> '
                '<span title="Az ödənilmiş məbləğ" '
                'style="cursor: help; color: #17a2b8; font-size: 12px;">ⓘ</span>',
                extra_amount
            )
        else:
            return format_html('<span style="color: #95a5a6;">{} ₼</span>', '0.00')
    
    extra_paid_amount_display.short_description = _("Əlavə Ödənilmiş")
    extra_paid_amount_display.admin_order_field = 'total_amount'

    def print_button(self, obj):
        """Display a print button for each calculation"""
        if obj.pk:
            url = reverse('admin:payments_paymentcalculation_print', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" style="background-color: #28a745; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px;">🖨️ Çap et</a>',
                url
            )
        return "-"
    
    print_button.short_description = _("Əməliyyat")
    print_button.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'calculate/',
                self.admin_site.admin_view(self.calculate_payments_view),
                name='payments_paymentcalculation_calculate'
            ),
            path(
                '<int:calculation_id>/print/',
                self.admin_site.admin_view(self.print_calculation_view),
                name='payments_paymentcalculation_print'
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['calculate_url'] = reverse('admin:payments_paymentcalculation_calculate')
        return super().changelist_view(request, extra_context)

    def calculate_payments_view(self, request):
        if request.method == 'POST':
            form = PaymentCalculationForm(request.POST)
            if form.is_valid():
                start_date = form.cleaned_data['start_date']
                end_date = form.cleaned_data['end_date']
                start_time = form.cleaned_data['start_time']
                end_time = form.cleaned_data['end_time']

                # Combine date and time for filtering
                start_datetime = datetime.combine(start_date, start_time)
                end_datetime = datetime.combine(end_date, end_time)

                # Make timezone aware
                if timezone.is_naive(start_datetime):
                    start_datetime = timezone.make_aware(start_datetime)
                if timezone.is_naive(end_datetime):
                    end_datetime = timezone.make_aware(end_datetime)

                # Filter payments by datetime range
                payments = Payment.objects.filter(
                    paid_at__gte=start_datetime,
                    paid_at__lte=end_datetime
                )

                # Calculate totals
                total_amount = payments.aggregate(
                    total=Sum('final_price')
                )['total'] or 0

                payment_count = payments.count()

                # Calculate amounts by payment type
                cash_amount = 0
                card_amount = 0
                other_amount = 0

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
                    created_by=request.user
                )
                
                # Save the payments to the calculation
                calculation.payments.set(payments)

                messages.success(
                    request,
                    _(f'Hesablama uğurla yaradıldı. Ümumi: {total_amount}₼, Sayı: {payment_count}')
                )

                return HttpResponseRedirect(
                    reverse('admin:payments_paymentcalculation_changelist')
                )
        else:
            form = PaymentCalculationForm()

        context = {
            'title': _('Ödəniş hesablaması'),
            'form': form,
            'opts': self.model._meta,
        }

        return render(request, 'admin/payments/payment_calculation_form.html', context)

    def has_add_permission(self, request):
        return False  # Don't allow manual addition, only through calculation

    def has_change_permission(self, request, obj=None):
        return False  # Read-only calculations

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superuser can delete calculations

    def print_calculation_view(self, request, calculation_id):
        """Print the payment calculation details"""
        from apps.printers.utils.service_v2 import PrinterService
        
        calculation = self.get_object(request, calculation_id)
        if not calculation:
            messages.error(request, _("Hesablama tapılmadı"))
            return HttpResponseRedirect(reverse('admin:payments_paymentcalculation_changelist'))
        
        try:
            success, message = PrinterService.print_payment_calculation(
                calculation=calculation,
                user=request.user
            )
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        except Exception as e:
            messages.error(request, _(f"Çap zamanı xəta baş verdi: {str(e)}"))
        
        return HttpResponseRedirect(reverse('admin:payments_paymentcalculation_changelist'))