from django.contrib import admin

from apps.payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'table',
        'final_price',
        'payment_type',
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
                'payment_type',
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

    orders_display.short_description = "Əlaqəli sifarişlər"
