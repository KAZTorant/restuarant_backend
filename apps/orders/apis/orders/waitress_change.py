from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.orders.models import Order

from apps.tables.models import Table
from apps.users.models import User

from apps.users.permissions import IsAdmin


class ChangeWaitressAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_description="Change an order's assigned waitress to the table.",
        responses={
            200: openapi.Response(description='Waitress successfully changed.'),
            404: 'Order not found or already paid, or table not found.'
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'new_waitress_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='New waitress ID')
            }
        )
    )
    def post(self, request, table_id):
        table: (Table | None) = Table.objects.filter(id=table_id).first()
        if not table:
            return Response(
                {'error': 'Masa tapılmadı!'},
                status=status.HTTP_404_NOT_FOUND
            )

        new_waitress_id = request.data.get("new_waitress_id", 0)
        new_waitress = User.objects.filter(
            type="waitress"
        ).filter(id=new_waitress_id).first()
        if not new_waitress:
            return Response(
                {'error': 'Dəyişmək istədiyiniz ofisiant tapılmadı!'},
                status=status.HTTP_404_NOT_FOUND
            )

        orders = table.orders.exclude(is_deleted=True).filter(is_paid=False)

        if not orders.exists():
            return Response(
                {'error': 'Sifariş yoxdur və ya ödəniş edilib.'},
                status=status.HTTP_404_NOT_FOUND
            )

        for o in orders:
            o.waitress = new_waitress
            o.save()

        # orders.update(waitress=new_waitress)
        return Response(
            {'error': 'Ofisiant uğurla dəyişdirildi.'},
            status=status.HTTP_200_OK
        )
