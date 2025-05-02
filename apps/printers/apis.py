import logging
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.printers.utils.service_v2 import PrinterService
from apps.users.permissions import AtMostAdmin
from apps.tables.models import Table


class PrintCheckAPIView(APIView):
    permission_classes = [IsAuthenticated, AtMostAdmin]

    def post(self, request, table_id):
        logging.error(f"Print, {table_id}")
        if not table_id:
            return Response({"error": "Table ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            printer = PrinterService()
            success, message = printer.print_orders_for_table(table_id)

            logging.error(f"Print, {success}, {message} ")
            if success:
                return Response({"message": message}, status=status.HTTP_200_OK)
            else:
                return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(f"Print, {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, table_id):
        if not table_id:
            return Response({"error": "Table ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        table = Table.objects.filter(id=table_id).first()
        if not table:
            return Response({"error": "Masa tapılmadı."}, status=status.HTTP_404_NOT_FOUND)
        orders = table.orders.exclude(is_deleted=True).filter(is_paid=False)
        if not orders.exists():
            return Response({"error": "Masa üçün sifariş tapılmadı."}, status=status.HTTP_404_NOT_FOUND)

        if table.can_print_check():
            return Response({"error": "Masa üçün çek print etmək mümkündür."}, status=status.HTTP_404_NOT_FOUND)
        orders.update()
        table.save()

        return Response({"success": True, "message": "Masa üçün yenidən çek print etmək mümkündür."}, status=status.HTTP_200_OK)
