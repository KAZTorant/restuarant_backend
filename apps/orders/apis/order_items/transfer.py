from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, serializers
from rest_framework.response import Response
from django.db import transaction

from apps.orders.models import OrderItem, Order
from apps.orders.serializers import OrderItemSerializer
from apps.tables.models import Table
from apps.users.permissions import IsAdmin
from apps.meals.models import Meal


class TransferOrderItemSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    order_item_id = serializers.IntegerField(required=False)
    meal_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    target_table_id = serializers.IntegerField()
    transfer_comment = serializers.CharField(allow_blank=True, required=False)

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value


class TransferOrderItemsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_description=(
            "Transfer a given number of confirmed order‐items (qty always = 1 each) "
            "of a specified meal from one order on the source table (URL) to the "
            "main unpaid order of another table (body). Creates the target main order "
            "if it doesn’t exist."
        ),
        request_body=TransferOrderItemSerializer,
        responses={
            status.HTTP_200_OK: OrderItemSerializer(many=True),
            status.HTTP_400_BAD_REQUEST: "Invalid input or insufficient items.",
            status.HTTP_404_NOT_FOUND: "Source/target table, order, or meal not found."
        }
    )
    def post(self, request, table_id):
        # 1. Validate input
        serializer = TransferOrderItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        src_order_id = serializer.validated_data["order_id"]
        meal_id = serializer.validated_data["meal_id"]
        qty = serializer.validated_data["quantity"]
        tgt_table_id = serializer.validated_data["target_table_id"]
        transfer_comment = serializer.validated_data.get(
            "transfer_comment", ""
        )
        order_item_id = serializer.validated_data.get(
            "order_item_id", 0
        )
        # 2. Fetch source table/order, target table, and meal
        try:
            src_table = Table.objects.get(pk=table_id)
            tgt_table = Table.objects.get(pk=tgt_table_id)
            src_order = Order.objects.get(pk=src_order_id, table=src_table)
            meal = Meal.objects.get(pk=meal_id)
        except (Table.DoesNotExist, Order.DoesNotExist, Meal.DoesNotExist):
            return Response(
                {"error": "Source/target table, order, or meal not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. Get or create the target table's main unpaid order
        tgt_order = self._get_or_create_main_order(request, tgt_table)

        # 4. Select exactly `qty` confirmed items of that meal
        if order_item_id:
            qty = 1
            items_qs = OrderItem.objects.filter(
                order=src_order,
                meal=meal,
                confirmed=True,
                id=order_item_id,
            ).order_by('id')[:qty]
        else:
            items_qs = OrderItem.objects.filter(
                order=src_order,
                meal=meal,
                confirmed=True
            ).order_by('id')[:qty]

        if items_qs.count() < qty:
            return Response(
                {"error": "Not enough confirmed items available for transfer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5. Transfer in a transaction
        try:
            with transaction.atomic():
                transferred = self._bulk_transfer(
                    items_qs,
                    tgt_order,
                    transfer_comment,
                )
                src_order.update_total_price()
                tgt_order.update_total_price()
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 6. Serialize and return
        data = OrderItemSerializer(transferred, many=True).data
        return Response(data, status=status.HTTP_200_OK)

    @staticmethod
    def _bulk_transfer(items_qs, new_order, transfer_comment=""):
        """
        Reassigns the given items to `new_order` in bulk,
        then returns the updated queryset for serialization.
        """
        pks = list(items_qs.values_list('pk', flat=True))
        order_items = OrderItem.objects.filter(pk__in=pks)
        order_items.update(
            order=new_order,
            transfer_comment=transfer_comment
        )
        return order_items

    @staticmethod
    def _get_or_create_main_order(request, table):
        """
        Returns the main unpaid order for `table`, creating one if needed.
        """
        # Try existing main, unpaid order
        existing = Order.objects.filter(
            table=table,
            is_main=True,
            is_paid=False
        ).first()
        if existing:
            return existing

        # Otherwise, create a new one
        return Order.objects.create(
            table=table,
            customer_count=1,
            waitress=request.user,
            is_main=True
        )
