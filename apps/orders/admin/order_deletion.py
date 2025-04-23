# apps/orders/admin.py

from django.contrib import admin
from apps.orders.models import OrderItemDeletionLog


@admin.register(OrderItemDeletionLog)
class OrderItemDeletionLogAdmin(admin.ModelAdmin):
    list_display = (
        'deleted_at',
        'order_id',
        'order_item_id',
        'table_id',
        'waitress_name',
        'meal_name',
        'quantity',
        'price',
        'customer_number',
        'reason',
        'deleted_by',
    )
    list_filter = (
        'reason',
        'deleted_at',
        'waitress_name',
        'table_id',
    )
    search_fields = (
        'meal_name',
        'waitress_name',
        'order_id',
        'order_item_id',
    )
    date_hierarchy = 'deleted_at'
    readonly_fields = (
        'order_id',
        'order_item_id',
        'table_id',
        'waitress_name',
        'meal_name',
        'quantity',
        'price',
        'customer_number',
        'reason',
        'deleted_by',
        'deleted_at',
    )
    ordering = ('-deleted_at',)
