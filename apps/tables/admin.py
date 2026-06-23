from django.contrib import admin
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, render
from django.urls import path

from apps.orders.models import Order
from apps.tables.models import Room, Table
from apps.tenants.admin_utils import filter_queryset_by_restaurant, get_user_restaurant
from apps.tenants.mixins import TenantAdminMixin


@admin.register(Room)
class RoomAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'is_active', 'restaurant')
    list_filter = ('is_active',)
    search_fields = ('name',)


class CustomTableAdmin(TenantAdminMixin, admin.ModelAdmin):
    tenant_lookup = 'room__restaurant'
    show_restaurant_in_list = False
    change_list_template = "admin/tables_changelist.html"
    list_display = ('number', 'room', 'capacity')
    actions = ['delete_selected']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('table/<int:table_id>/orders/',
                 self.admin_site.admin_view(self.orders_view), name='table_active_order'),
        ]
        return custom_urls + urls

    def orders_view(self, request, table_id):
        restaurant = get_user_restaurant(request.user)
        table_qs = filter_queryset_by_restaurant(
            Table.objects.filter(pk=table_id), restaurant, 'room__restaurant',
        )
        table = get_object_or_404(table_qs)
        orders = Order.objects.filter(table=table, is_paid=False)
        total_quantity = orders.aggregate(total_quantity=Sum(
            'order_items__quantity'))['total_quantity'] or 0
        total_price = orders.aggregate(total_price=Sum(
            F('order_items__quantity') * F('order_items__price')))['total_price'] or 0

        return render(
            request,
            'admin/orders_modal.html',
            {
                'table': table,
                'orders': orders,
                'total_quantity': total_quantity,
                'total_price': total_price,
            }
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('room', 'number')

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        try:
            cl = response.context_data['cl']
            restaurant = get_user_restaurant(request.user)
            cl.rooms = filter_queryset_by_restaurant(Room.objects.all(), restaurant)
            for table in cl.result_list:
                table.has_unpaid_orders = Order.objects.exclude(
                    is_deleted=True).filter(table=table, is_paid=False).exists()
        except (AttributeError, KeyError):
            pass
        return response


admin.site.register(Table, CustomTableAdmin)
