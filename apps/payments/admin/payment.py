from django.contrib import admin
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
        
        for item in order.order_items.all():
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
