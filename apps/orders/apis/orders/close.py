from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.printers.utils.service import PrinterService
from apps.tables.models import Table

from apps.users.permissions import IsAdmin


class CloseTableOrderAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request, table_id):

        table = Table.objects.filter(id=table_id).first()
        if not table:
            return Response(
                {
                    "errors": 'Masa tapılmadı.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        orders = table.orders.exclude(is_deleted=True).filter(is_paid=False)

        if not orders.exists():
            return Response(
                {"success": False, "message": "Masada sifariş yoxdur."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            printer = PrinterService()
            printer.print_orders_for_table(table_id, False)
        except Exception as e:
            print("Printer error", str(e))

        # orders.update(is_paid=True)
        for o in orders:
            o.is_paid = True
            o.save()

        return Response(
            {"success": True, "message": "Sifariş uğurla bağlamşdır."},
            status=status.HTTP_200_OK
        )
