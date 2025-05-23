from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.payments.models import Payment, PaymentMethod


class PaymentMethodInline(admin.TabularInline):
    model = PaymentMethod
    extra = 0
    readonly_fields = ('created_at',)


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
    inlines = [PaymentMethodInline]
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
