from drf_yasg.utils import swagger_auto_schema

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.meals.models import Meal
from apps.orders.models import OrderItem
from apps.orders.models.order import Order
from apps.orders.serializers import OrderItemSerializer
from apps.tables.models import Table
from apps.users.permissions import AtMostAdmin


class AddOrderItemAPIView(APIView):
    permission_classes = [IsAuthenticated, AtMostAdmin]

    @swagger_auto_schema(
        operation_description=(
            "Add a meal to an existing unpaid order for the specified table, "
            "associating the meal with a specific customer number. "
            "This endpoint always creates a new unconfirmed order item "
            "with a fixed quantity of 1."
        ),
        request_body=OrderItemSerializer,
        responses={
            status.HTTP_200_OK: OrderItemSerializer,
            status.HTTP_404_NOT_FOUND: 'Order or meal not found or access denied.',
            status.HTTP_400_BAD_REQUEST: 'Invalid data'
        }
    )
    def post(self, request, table_id):
        order_id = (request.data or {}).get("order_id")
        meal_id = (request.data or {}).get("meal_id")
        customer_number = (request.data or {}).get("customer_number", 1)

        if not customer_number:
            return Response(
                {"error": "customer_number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order = self.get_order(request, table_id, order_id)
        if not order:
            return Response(
                {'error': 'Order not found or payment has been made already.'},
                status=status.HTTP_404_NOT_FOUND
            )

        meal = self.get_meal(meal_id)
        if not meal:
            return Response(
                {'error': 'Meal not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            with transaction.atomic():
                order_item = self.create_order_item(
                    order, meal, customer_number)
                order.update_total_price()
        except Exception as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        serializer = OrderItemSerializer(order_item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_order(self, request, table_id, order_id):
        """
        Retrieves the order for the specified table.
        If an order_id is provided, fetch it from table.current_orders;
        otherwise, use table.current_order.
        Also verifies that the requesting user has access.
        """
        try:
            table = Table.objects.get(id=table_id)
        except Table.DoesNotExist:
            return None

        order = (
            table.current_orders.filter(id=order_id).first()
            if order_id
            else table.current_order
        )

        if order and (
            request.user.type in ["admin", "captain_waitress", "restaurant"]
            or order.waitress == request.user
        ):
            return order

        return None

    def get_meal(self, meal_id):
        """
        Retrieves a Meal instance by its ID.
        """
        try:
            return Meal.objects.get(id=meal_id)
        except Meal.DoesNotExist:
            return None

    def create_order_item(self, order, meal, customer_number):
        """
        Always create a new order item for the given meal and customer.
        The order item will have:
          - A fixed quantity of 1.
          - The price set to the meal's price.
          - A confirmed flag set to False (unconfirmed).
        """
        return OrderItem.objects.create(
            order=order,
            meal=meal,
            customer_number=customer_number,
            quantity=1,        # Fixed quantity, never changed.
            price=meal.price,
            confirmed=False    # New order items start as unconfirmed.
        )
