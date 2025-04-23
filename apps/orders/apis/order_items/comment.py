# apps/orders/api/add_comment.py

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from apps.orders.models import OrderItem
from apps.orders.serializers import AddCommentToOrderItemSerializer
from apps.tables.models import Table
from apps.users.permissions import AtMostAdmin


class AddCommentToOrderItemAPIView(APIView):
    permission_classes = [IsAuthenticated, AtMostAdmin]

    @swagger_auto_schema(
        operation_description="""
        Add the same comment to all non-confirmed OrderItem(s) for a given meal 
        in the specified order (if order_id provided) or in the current unpaid main order.
        """,
        request_body=AddCommentToOrderItemSerializer,
        responses={
            200: 'Updated count of items',
            404: 'Order or items not found',
            400: 'Invalid data'
        }
    )
    def post(self, request, table_id):
        # 1) Load table
        try:
            table = Table.objects.get(pk=table_id)
        except Table.DoesNotExist:
            return Response({"error": "Stol tapılmadı."},
                            status=status.HTTP_404_NOT_FOUND)

        # 2) Validate payload
        serializer = AddCommentToOrderItemSerializer(
            data=request.data, context={"table": table}
        )
        serializer.is_valid(raise_exception=True)
        meal_id = serializer.validated_data["meal_id"]
        comment = serializer.validated_data["comment"]

        # 3) Determine target order
        order_id = request.data.get("order_id")
        if order_id:
            order = table.orders.exclude(is_deleted=True)\
                .filter(is_paid=False, id=order_id).first()
        else:
            order = table.orders.exclude(is_deleted=True)\
                .filter(is_paid=False, is_main=True)\
                .first()

        if not order:
            return Response(
                {"error": "Uyğun aktiv sifariş tapılmadı."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4) Bulk‐find & update non-confirmed items
        items_qs = OrderItem.objects.filter(
            order=order,
            meal_id=meal_id,
            confirmed=False
        )
        if not items_qs.exists():
            return Response(
                {"error": "Uyğun təsdiqlənməmiş məhsul tapılmadı."},
                status=status.HTTP_404_NOT_FOUND
            )

        updated_count = items_qs.update(comment=comment)

        # 5) Return summary
        return Response({"updated": updated_count}, status=status.HTTP_200_OK)
