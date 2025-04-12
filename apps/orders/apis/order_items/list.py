from collections import defaultdict
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response

from apps.orders.serializers import ListOrderItemSerializer
from apps.orders.models import Order, OrderItem
from apps.tables.models import Table
from apps.users.permissions import IsWaitressOrCapitaonOrAdminOrOwner


class ListOrderItemsAPIView(ListAPIView):
    serializer_class = ListOrderItemSerializer
    permission_classes = [IsAuthenticated, IsWaitressOrCapitaonOrAdminOrOwner]

    def get_queryset(self):
        """
        Retrieves the raw order items from the current order for the specified table.
        (Grouping will be performed in the 'list' method.)
        """
        table_id = self.kwargs.get("table_id", 0)
        table = Table.objects.filter(id=table_id).first()
        if not table:
            return OrderItem.objects.none()

        default_order_id = table.current_order.id if table.current_order else None
        if not default_order_id:
            return OrderItem.objects.none()

        # Use the provided order_id from GET (if any) or the default order.
        order_id = self.request.GET.get("order_id", default_order_id)
        order = table.current_orders.filter(id=order_id).first()
        if not order:
            return OrderItem.objects.none()

        return order.order_items.order_by('-item_added_at').all()

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'order_id',
                openapi.IN_QUERY,
                description="Filter by order ID",
                type=openapi.TYPE_STRING
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        # Get all raw order items for this order.
        queryset = self.get_queryset()

        # Group order items by (meal, confirmed). The key is a tuple: (meal.id, confirmed flag).
        groups = {}
        for item in queryset:
            key = (item.meal.id, item.confirmed)
            if key not in groups:
                groups[key] = {
                    'meal': item.meal,
                    'confirmed': item.confirmed,
                    'quantity': 0,
                    'price': 0,
                    # We'll choose the latest timestamp in the group.
                    'item_added_at': item.item_added_at
                }
            # In current logic, each item quantity is 1.
            groups[key]['quantity'] += item.quantity
            # Aggregated price = sum(prices) for the group.
            groups[key]['price'] += item.price
            # Update the timestamp to the latest one found.
            if item.item_added_at and item.item_added_at > groups[key]['item_added_at']:
                groups[key]['item_added_at'] = item.item_added_at

        # Create "dummy" OrderItem instances for aggregated groups.
        aggregated_items = []
        for key, data in groups.items():
            dummy_item = OrderItem()
            # Dummy ID since this is an aggregated result.
            dummy_item.id = None
            dummy_item.meal = data['meal']
            dummy_item.confirmed = data['confirmed']
            dummy_item.quantity = data['quantity']
            dummy_item.price = data['price']
            dummy_item.item_added_at = data['item_added_at']
            aggregated_items.append(dummy_item)

        # Now sort the aggregated items by meal.
        # For example, sort by meal name, and for same meal, unconfirmed items come before confirmed.
        aggregated_items = sorted(
            aggregated_items, key=lambda x: (x.meal.name, x.confirmed))

        serializer = self.get_serializer(aggregated_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
