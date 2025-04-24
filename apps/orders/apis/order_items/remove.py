# apps/orders/api/remove_refactored.py

from decimal import Decimal
from django.db.models import Sum
from django.db import models

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from apps.inventory_connector.signals import OrderItemInventoryManager
from apps.orders.models.order_deletion import OrderItemDeletionLog
from apps.orders.serializers import DeleteOrderItemV2Serializer
from apps.tables.models import Table
from apps.users.permissions import IsAdmin


class DeleteOrderItemAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_description=(
            "Decrease the quantity or delete an item from an existing unpaid order for the specified table. "
            "For confirmed items, you must supply reason='return' or 'waste' and may include a reason_comment."
        ),
        request_body=DeleteOrderItemV2Serializer,
        responses={
            204: 'Item updated or deleted successfully',
            404: 'Order or item not found, or payment already made',
            400: 'Invalid data'
        }
    )
    def delete(self, request, table_id):
        order = self._get_order(table_id, request.data.get("order_id"))
        if order is None:
            return self._response_not_found('Sifariş yoxdur və ya ödəniş edilib')

        meal_id = request.data.get("meal_id")
        confirmed = request.data.get("confirmed", False)
        order_item_id = int(request.data.get("order_item_id", 0))

        order_item = self._get_order_item(
            order,
            meal_id,
            confirmed,
            order_item_id,
        )
        if order_item is None:
            return self._response_not_found('Sifariş məhsulu tapılmadı')

        # Extract reason and optional comment
        reason = request.data.get("reason")
        comment = request.data.get("reason_comment", "")

        if order_item.confirmed:
            error_response = self._validate_reason(reason)
            if error_response:
                return error_response
            self._handle_confirmed(
                order, order_item, reason, comment, request.user)
        else:
            self._handle_unconfirmed(order_item)

        self._recalculate_order(order)
        return self._finalize_order_response(order)

    @staticmethod
    def _get_order(table_id, order_id):
        try:
            table = Table.objects.get(pk=table_id)
        except Table.DoesNotExist:
            return None

        queryset = table.orders.exclude(is_deleted=True).filter(is_paid=False)
        if order_id:
            return queryset.filter(id=order_id).first()
        return queryset.filter(is_main=True).first()

    @staticmethod
    def _get_order_item(order, meal_id, confirmed=False, order_item_id=0):
        if order_item_id:
            return order.order_items.filter(id=order_item_id).first()

        return (
            order.order_items
            .filter(meal__id=meal_id)
            .filter(confirmed=confirmed)
            .first()
        )

    @staticmethod
    def _validate_reason(reason):
        valid_reasons = (
            OrderItemDeletionLog.REASON_RETURN,
            OrderItemDeletionLog.REASON_WASTE
        )
        if reason not in valid_reasons:
            return Response(
                {'error': "Təsdiqlənmişlər üçün reason='return' və ya 'waste' tələb olunur."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return None

    @staticmethod
    def _handle_confirmed(order, order_item, reason, comment, user):
        waitress_name = order.waitress.get_full_name() if order.waitress else ''

        if order_item.quantity > 1:
            DeleteOrderItemAPIView._decrement_and_log_single(
                order, order_item, reason, comment, waitress_name, user
            )
        else:
            # full delete with comment
            order_item.delete(reason=reason, deleted_by=user, comment=comment)

    @staticmethod
    def _handle_unconfirmed(order_item):
        order_item.delete()

    @staticmethod
    def _decrement_and_log_single(order, order_item, reason, comment, waitress_name, user):
        unit_price = order_item.meal.price
        order_item.quantity -= 1
        order_item.price = order_item.quantity * unit_price
        order_item.save()

        # Log the single-item deletion with comment
        OrderItemDeletionLog.objects.create(
            order_id=order.pk,
            order_item_id=order_item.pk,
            table_id=order.table_id,
            waitress_name=waitress_name,
            meal_name=order_item.meal.name,
            quantity=1,
            price=unit_price,
            customer_number=order_item.customer_number,
            reason=reason,
            deleted_by=user,
            comment=comment
        )

        # Return inventory if appropriate
        if reason == OrderItemDeletionLog.REASON_RETURN:
            OrderItemInventoryManager._process_mappings(order_item, 'add')

    @staticmethod
    def _recalculate_order(order):
        total = order.order_items.aggregate(
            total=Sum('price', output_field=models.DecimalField())
        )['total'] or Decimal(0)
        order.total_price = total
        order.save()

    @staticmethod
    def _finalize_order_response(order):
        if not order.order_items.exists():
            order.is_deleted = True
            order.save()
            return Response(
                {'error': 'Sifariş artıq mövcud deyil'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _response_not_found(message):
        return Response(
            {'error': message},
            status=status.HTTP_404_NOT_FOUND
        )
