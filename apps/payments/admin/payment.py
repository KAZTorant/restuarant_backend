from decimal import Decimal
from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from apps.orders.models import Order
from apps.payments.models import Payment, PaymentMethod


class PaymentMethodInline(admin.TabularInline):
    model = PaymentMethod
    extra = 0
    readonly_fields = ('created_at',)


class OrderInline(admin.TabularInline):
    model = Payment.orders.through
    extra = 0
    verbose_name = _("Sifariş")
    verbose_name_plural = _("Sifarişlər")
    readonly_fields = ('order_details',)
    fields = ('order_details',)
    can_delete = False

    def order_details(self, obj):
        if not obj.order:
            return "-"
        
        order = obj.order
        
        # Group items by meal name and unit price
        from collections import defaultdict
        grouped_items = defaultdict(lambda: {'quantity': 0, 'unit_price': 0, 'total': 0})
        
        for item in order.order_items.all_order_items().filter(order=order):
            # Calculate unit price from total price and quantity
            unit_price = item.price / item.quantity if item.quantity > 0 else 0
            key = (item.meal.name, unit_price)
            grouped_items[key]['quantity'] += item.quantity
            grouped_items[key]['unit_price'] = unit_price
            grouped_items[key]['total'] += item.price
        
        # Sort by meal name
        sorted_items = sorted(grouped_items.items(), key=lambda x: x[0][0])
        
        items_html = []
        for (meal_name, unit_price), data in sorted_items:
            items_html.append(
                f"<tr>"
                f"<td style='padding: 8px; border: 1px solid #ddd;'>{meal_name}</td>"
                f"<td style='padding: 8px; text-align: center; border: 1px solid #ddd;'>{data['quantity']}</td>"
                f"<td style='padding: 8px; text-align: right; border: 1px solid #ddd;'>{unit_price:.2f}₼</td>"
                f"<td style='padding: 8px; text-align: right; border: 1px solid #ddd;'>{data['total']:.2f}₼</td>"
                f"</tr>"
            )
        
        html = f"""
        <div style="margin: 10px 0;">
            <strong>Sifariş #{order.id}</strong> - 
            <span style="color: #666;">Masa: {order.table.number}</span> - 
            <span style="color: #666;">Ümumi: {order.total_price}₼</span>
            <table style="width: 100%; margin-top: 10px; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Məhsul</th>
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;">Say</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Qiymət</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Cəmi</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(items_html)}
                </tbody>
            </table>
        </div>
        """
        return mark_safe(html)
    
    order_details.short_description = _("Sifariş təfərrüatları")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'table',
        'final_price',
        'payment_methods_display',
        'paid_by',
        'paid_at',
        'reprint_button',
    )
    list_filter = (
        'payment_type',
        'paid_at',
        'table',
        'paid_by',
    )
    search_fields = (
        'table__number',
        'paid_by__username',
        'discount_comment',
    )
    readonly_fields = (
        'paid_at',
        'paid_by',
        'orders_display',
    )
    inlines = [PaymentMethodInline, OrderInline]
    fieldsets = (
        (None, {
            'fields': (
                'table',
                'orders_display',
                'total_price',
                'discount_amount',
                'discount_comment',
                'final_price',
                'paid_amount',
                'change',
                'paid_by',
                'paid_at',
            )
        }),
    )

    def orders_display(self, obj):
        return ", ".join([
            f"#{order.id} - {order.total_price}₼"
            for order in obj.orders.all()
        ]) or "Yoxdur"
    orders_display.short_description = _("Əlaqəli sifarişlər")

    def payment_methods_display(self, obj):
        if obj.payment_methods.exists():
            return ", ".join([
                f"{method.get_payment_type_display()}: {method.amount}₼"
                for method in obj.payment_methods.all()
            ])
        return f"{obj.get_payment_type_display()}: {obj.paid_amount}₼"
    payment_methods_display.short_description = _("Ödəniş növləri")

    def reprint_button(self, obj):
        url = f"reprint/{obj.pk}/"
        return format_html(
            '<a class="button" href="{}" style="'
            'background:#417690;color:#fff;padding:4px 10px;'
            'border-radius:4px;text-decoration:none;font-size:12px;">'
            '🖨 Çek çap et</a>',
            url
        )
    reprint_button.short_description = _("Çap")
    reprint_button.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'reprint/<int:payment_id>/',
                self.admin_site.admin_view(self.reprint_receipt_view),
                name='payment_reprint',
            ),
        ]
        return custom + urls

    def reprint_receipt_view(self, request, payment_id):
        from apps.printers.utils.service_v2 import PrinterService

        try:
            payment = Payment.objects.get(pk=payment_id)
        except Payment.DoesNotExist:
            self.message_user(request, "Ödəmə tapılmadı.", level=messages.ERROR)
            return redirect('../../')

        orders = payment.orders.all()
        if not orders.exists():
            self.message_user(request, "Bu ödəməyə aid sifariş yoxdur.", level=messages.ERROR)
            return redirect('../../')

        table = payment.table

        # Collect payment methods
        if payment.payment_methods.exists():
            payment_methods_data = [
                {'payment_type': m.payment_type, 'amount': str(m.amount)}
                for m in payment.payment_methods.all()
            ]
            payment_type = None
        else:
            payment_methods_data = None
            payment_type = payment.payment_type

        receipt_data = PrinterService._build_receipt_data(
            table=table,
            orders=orders,
            is_paid=True,
            payment_type=payment_type,
            payment_methods=payment_methods_data,
            discount_amount=Decimal(str(payment.discount_amount or 0)),
            discount_comment=payment.discount_comment or "",
            paid_amount=Decimal(str(payment.paid_amount or 0)),
            change=Decimal(str(payment.change or 0)),
        )

        formatted_text = PrinterService._format_customer_receipt(receipt_data)
        response = PrinterService._send_text_to_main_printer(formatted_text)

        if response.status_code == 200:
            self.message_user(request, f"#{payment_id} ödəməsinin çeki uğurla çap edildi.")
        else:
            self.message_user(request, "Printer qoşulmayıb və ya xəta baş verdi.", level=messages.ERROR)

        return redirect('../../')
