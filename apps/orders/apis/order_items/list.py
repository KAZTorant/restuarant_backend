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
from apps.users.permissions import AtMostAdmin


class ListOrderItemsAPIView(ListAPIView):
    serializer_class = ListOrderItemSerializer
    permission_classes = [IsAuthenticated, AtMostAdmin]

    def get_queryset(self):
        """
        Retrieves the raw order items from the current order for the specified table.
        (Grouping will be performed in the 'list' method.)
        """
        table_id = self.kwargs.get("table_id", 0)
        table = Table.objects.filter(id=table_id).first()
        if not table:
            return OrderItem.objects.none()

        default_order_id = table.orders.exclude(is_deleted=True).filter(is_paid=False, is_main=True).first(
        ).id if table.orders.exclude(is_deleted=True).filter(is_paid=False, is_main=True).first() else None
        if not default_order_id:
            return OrderItem.objects.none()

        order_id = self.request.GET.get("order_id", default_order_id)
        order = table.orders.exclude(is_deleted=True).filter(
            is_paid=False).filter(id=order_id).first()
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
        queryset = self.get_queryset()

        # Group order items by meal, confirmed flag, and customer_number.
        groups = {}
        for item in queryset:
            key = (item.meal.id, item.confirmed, item.customer_number)
            if item.meal.is_extra:
                key = (
                    item.meal.id, item.confirmed,
                    item.customer_number, item.id
                )
            if key not in groups:
                groups[key] = {
                    'meal': item.meal,
                    'confirmed': item.confirmed,
                    'customer_number': item.customer_number,
                    'quantity': 0,
                    'price': 0,
                    # Latest timestamp in the group.
                    'item_added_at': item.item_added_at,
                    'comment': set(),
                    'order_item_id': item.id if item.meal.is_extra else 0
                }
            groups[key]['quantity'] += item.quantity
            groups[key]['price'] += item.price

            if getattr(item, 'comment', None):
                groups[key]['comment'].add(item.comment.strip())

            if item.item_added_at and item.item_added_at > groups[key]['item_added_at']:
                groups[key]['item_added_at'] = item.item_added_at

        aggregated_items = []
        for key, data in groups.items():
            dummy_item = OrderItem()
            dummy_item.id = None  # Dummy ID for aggregated result.
            dummy_item.meal = data['meal']
            dummy_item.confirmed = data['confirmed']
            dummy_item.customer_number = data['customer_number']
            dummy_item.quantity = data['quantity']
            dummy_item.price = data['price']
            dummy_item.item_added_at = data['item_added_at']
            dummy_item.comment = "".join(sorted(data['comment']))
            dummy_item.order_item_id = data.get("order_item_id")
            aggregated_items.append(dummy_item)

        # Sort aggregated items by meal name, then by customer_number, then by confirmed flag.
        aggregated_items = sorted(
            aggregated_items,
            key=lambda x: (
                x.meal.name, x.customer_number, x.confirmed
            )
        )

        serializer = self.get_serializer(aggregated_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
