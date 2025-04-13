from datetime import datetime
from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.tables.models import Table
from apps.printers.utils.service import PrinterService


class ConfirmOrderItemsToWorkerPrintersAPIView(APIView):
    """
    API endpoint to confirm unconfirmed order items for a table's current order and send
    formatted receipt texts to worker printers. Order items are grouped by meal so that the worker
    sees the aggregated quantity per meal.
    """
    @swagger_auto_schema(
        operation_description=(
            "Confirms unconfirmed order items for the current order of a given table, groups them by the "
            "preparation place (which determines the worker printer), generates a formatted receipt text for each "
            "printer with aggregated meal quantities, and sends the text using a worker printer service."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['table_id'],
            properties={
                'table_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="ID of the table for which order items are to be confirmed"
                )
            }
        ),
        responses={
            200: openapi.Response(description="Order items confirmed and receipts sent"),
            400: "Missing or invalid table_id",
            404: "Table or current order not found",
            500: "Internal error"
        }
    )
    def post(self, request, *args, **kwargs):
        table_id = request.data.get('table_id')
        if not table_id:
            return Response({"error": "table_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        table = self.get_table(table_id)
        if table is None:
            return Response({"error": "Table not found"}, status=status.HTTP_404_NOT_FOUND)

        order = self.get_current_order(table)
        if order is None:
            return Response(
                {"error": "No current order found for this table"},
                status=status.HTTP_404_NOT_FOUND
            )

        unconfirmed_items = self.get_unconfirmed_order_items(order)
        if not unconfirmed_items.exists():
            return Response(
                {"message": "No unconfirmed order items found"},
                status=status.HTTP_200_OK
            )

        # Group unconfirmed order items by worker printer.
        printer_groups = self.group_items_by_worker_printer(unconfirmed_items)

        try:
            self.confirm_order_items(printer_groups)
        except Exception as e:
            return Response(
                {"error": f"Error confirming order items: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Generate and send receipt texts for each printer group.
        printer_service = PrinterService()
        receipt_results = {}
        for printer, items in printer_groups.items():
            receipt_data = self.prepare_receipt_data(order, items)
            response = printer_service.send_to_worker_printer(
                receipt_data, printer)
            receipt_results[str(printer.id)] = response.status_code

        return Response(
            {
                "message": "Order items confirmed and receipts sent",
                "receipt_results": receipt_results
            },
            status=status.HTTP_200_OK
        )

    def get_table(self, table_id):
        """Retrieve the table by ID."""
        try:
            return Table.objects.get(pk=table_id)
        except Table.DoesNotExist:
            return None

    def get_current_order(self, table):
        """Return the current order of a given table."""
        return table.current_order

    def get_unconfirmed_order_items(self, order):
        """Retrieve unconfirmed order items for the order."""
        return order.order_items.filter(confirmed=False)

    def group_items_by_worker_printer(self, unconfirmed_items):
        """
        Groups order items by their worker printer based on the meal's preparation place.

        Returns:
            dict: Keys are Printer instances, and values are lists of OrderItem instances.
        """
        groups = {}
        for item in unconfirmed_items:
            # Assume each Meal has a related preparation_place with a printer.
            prep_place = item.meal.preparation_place
            if not prep_place:
                continue  # Skip if no preparation place is assigned.
            printer = prep_place.printer
            if not printer:
                continue  # Skip if no printer is configured.
            if printer not in groups:
                groups[printer] = []
            groups[printer].append(item)
        return groups

    def confirm_order_items(self, printer_groups):
        """
        Marks all order items in the provided groups as confirmed inside an atomic transaction.
        """
        with transaction.atomic():
            for items in printer_groups.values():
                for item in items:
                    item.confirmed = True
                    item.save(update_fields=['confirmed'])

    def prepare_receipt_data(self, order, items):
        """
        Prepares a receipt data dictionary. Order items are grouped by meal so that if there are 
        multiple order items for the same meal, they are combined into one entry with an aggregated quantity.
        """
        # Group items by meal
        meal_groups = {}
        for item in items:
            meal_id = item.meal.id
            if meal_id not in meal_groups:
                meal_groups[meal_id] = {
                    "name": item.meal.name,
                    "quantity": 0,
                    # Assuming price per unit is constant.
                    "price": item.meal.price,
                    "line_total": 0
                }
            meal_groups[meal_id]["quantity"] += item.quantity

        # Compute line_total for each grouped meal.
        for group in meal_groups.values():
            group["line_total"] = group["quantity"] * group["price"]

        # Create a list of grouped items.
        grouped_items = list(meal_groups.values())
        order_total = sum(item["line_total"] for item in grouped_items)

        receipt_data = {
            "date": datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            "table": {
                "room": order.table.room.name if order.table and order.table.room else "N/A",
                "number": order.table.number if order.table else "N/A"
            },
            "orders": [{
                "order_id": order.id,
                "items": grouped_items,
                "order_total": order_total
            }]
        }
        return receipt_data
