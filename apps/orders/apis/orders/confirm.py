from datetime import datetime
from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.tables.models import Table
from apps.printers.utils.service_v2 import PrinterService
from apps.users.permissions import AtMostAdmin


class ConfirmOrderItemsToWorkerPrintersAPIView(APIView):
    """
    API endpoint to confirm unconfirmed order items for a table's orders and send
    formatted receipt texts to worker printers. The table id is passed in the URL.
    In the request body, an optional "order_id" can be provided:
      - If provided, only that order is processed.
      - Otherwise, all current orders for the table are processed.
    Order items are grouped by meal (aggregated by quantity) before sending.
    """

    permission_classes = [IsAuthenticated, AtMostAdmin]

    @swagger_auto_schema(
        operation_description=(
            "Confirms unconfirmed order items for the current order(s) of a given table. "
            "If 'order_id' is provided in the request body, only that order is processed; otherwise, "
            "all current orders for the table are processed. Order items are grouped by preparation place (which "
            "determines the worker printer), and a formatted receipt text with aggregated meal quantities is "
            "generated and sent to each corresponding worker printer."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['table_id'],
            properties={
                'order_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Optional ID of the order to confirm. If not provided, all orders are processed."
                ),
            }
        ),
        responses={
            200: openapi.Response(description="Order items confirmed and receipts sent"),
            400: "Missing or invalid table_id",
            404: "Table or order(s) not found",
            500: "Internal error"
        }
    )
    def post(self, request, table_id, *args, **kwargs):
        # Get the table from the URL parameter
        table = self.get_table(table_id)
        if table is None:
            return Response({"error": "Table not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get the optional order_id from the request body
        order_id = request.data.get('order_id')

        # Retrieve target orders for this table
        orders = self.get_target_orders(table, order_id)
        if not orders:
            return Response({"error": "No order(s) found for this table."}, status=status.HTTP_404_NOT_FOUND)

        # Combine unconfirmed order items from all target orders
        unconfirmed_items = []
        for order in orders:
            unconfirmed_items.extend(
                list(order.order_items.filter(confirmed=False))
            )
        if not unconfirmed_items:
            return Response({"message": "No unconfirmed order items found"}, status=status.HTTP_200_OK)

        # Group unconfirmed order items by worker printer
        printer_groups = self.group_items_by_worker_printer(unconfirmed_items)

        try:
            self.confirm_order_items(printer_groups)
        except Exception as e:
            return Response({"error": f"Error confirming order items: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Generate and send receipt texts for each printer group
        receipt_results = {}
        for printer, items in printer_groups.items():
            receipt_data = self.prepare_receipt_data(orders, items)
            response = PrinterService.send_to_worker_printer(
                receipt_data,
                printer,
                orders,
            )
            receipt_results[str(printer.id)] = response.status_code

        return Response(
            {"message": "Order items confirmed and receipts sent",
                "receipt_results": receipt_results},
            status=status.HTTP_200_OK
        )

    def get_table(self, table_id):
        try:
            return Table.objects.get(pk=table_id)
        except Table.DoesNotExist:
            return None

    def get_target_orders(self, table, order_id=None):
        if order_id:
            order = table.orders.exclude(is_deleted=True).filter(
                is_paid=False).filter(id=order_id).first()
            return [order] if order else []
        else:
            return list(table.orders.exclude(is_deleted=True).filter(is_paid=False).all())

    def group_items_by_worker_printer(self, unconfirmed_items):
        groups = {}
        for item in unconfirmed_items:
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
        with transaction.atomic():
            for items in printer_groups.values():
                for item in items:
                    item.confirmed = True
                    item.save(update_fields=['confirmed'])

    def prepare_receipt_data(self, orders, items):
        # Determine the order ID string and table reference
        if len(orders) == 1:
            order_id_str = str(orders[0].id)
            table = orders[0].table
        else:
            order_id_str = ", ".join(str(o.id) for o in orders)
            table = orders[0].table

        # Group items by meal and aggregate quantities + collect comments
        meal_groups = {}
        for item in items:
            mid = item.meal.id
            if mid not in meal_groups:
                meal_groups[mid] = {
                    "name":       item.meal.name,
                    "quantity":   0,
                    "price":      item.meal.price,
                    "line_total": 0,
                    "comments":   set(),      # collect into a set
                }
            grp = meal_groups[mid]
            grp["quantity"] += item.quantity

            # collect any non-empty comment
            comment = getattr(item, "comment", None)
            if comment and comment.strip():
                grp["comments"].add(comment.strip())

        # Finalize each group: compute line_total and turn comments into a sorted list
        grouped_items = []
        for grp in meal_groups.values():
            grp["line_total"] = grp["quantity"] * grp["price"]
            grp["comments"] = sorted(grp["comments"])
            grouped_items.append(grp)

        # Compute order_total once per the grouped items
        order_total = sum(g["line_total"] for g in grouped_items)

        # Build the receipt payload
        receipt_data = {
            "date": datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            "table": {
                "room":   table.room.name if table and table.room else "N/A",
                "number": table.number if table else "N/A"
            },
            "orders": [{
                "order_id":    order_id_str,
                "items":       grouped_items,
                "order_total": order_total
            }]
        }
        return receipt_data
