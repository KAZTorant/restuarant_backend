from django.contrib import admin, messages
from django.urls import path
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.db.models import Min, Max, Sum, Q
from datetime import datetime, timedelta
from decimal import Decimal

from simple_history.admin import SimpleHistoryAdmin
from apps.orders.models import Summary, Statistics, Order, OrderItem
from apps.printers.utils.service_v2 import PrinterService
from apps.printers.models.receipt import Receipt
from apps.payments.models import Payment


@admin.register(Summary)
class SummaryAdmin(SimpleHistoryAdmin):
    """
    Admin for date-range Summary reports.
    """
    list_display = (
        'date_range_display', 'total', 'cash_total', 'card_total', 'other_total', 'created_by', 'created_at'
    )
    list_filter = ('created_by', 'created_at')
    readonly_fields = [
        'start_date', 'end_date', 'statistics',
        'cash_total', 'card_total', 'other_total', 'total',
        'created_by', 'created_at'
    ]
    fieldsets = (
        ('📅 Tarix məlumatları', {
            'fields': ('start_date', 'end_date'),
        }),
        ('💰 Məbləğlər', {
            'fields': (
                'cash_total', 'card_total', 'other_total', 'total',
            ),
        }),
        ('📋 Əlavə məlumat', {
            'fields': (
                'created_by', 'created_at',
            ),
        }),
    )
    change_list_template = 'admin/summary_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('date-range-summary/',
                 self.admin_site.admin_view(self.date_range_summary_view),
                 name='orders_summary_date_range'),
            path('create-summary/',
                 self.admin_site.admin_view(self.create_summary_view),
                 name='orders_summary_create'),
            path('<int:summary_id>/print-summary/',
                 self.admin_site.admin_view(self.print_summary_view),
                 name='orders_summary_print'),
            path('<int:summary_id>/preview-summary/',
                 self.admin_site.admin_view(self.preview_summary_view),
                 name='orders_summary_preview'),
        ]
        return custom + urls

    def has_add_permission(self, request):
        # Creation only via date range modal
        return False

    def date_range_display(self, obj):
        return obj.date_range_display
    date_range_display.short_description = "Tarix aralığı"

    def date_range_summary_view(self, request):
        """Handle the modal view for selecting a date range."""
        context = {
            'title': 'Ümumi Hesabat Yaratma',
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
        }
        return self.render_date_range_form(request, 'admin/summary_date_range_form.html', context)

    def render_date_range_form(self, request, template, context):
        """Helper method to render the date range form."""
        from django.shortcuts import render

        return render(request, template, context)

    def create_summary_view(self, request):
        """Create a new Summary record from a date range."""
        if request.method != 'POST':
            return HttpResponseRedirect('..')

        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Validate dates
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

            if start_date > end_date:
                self.message_user(
                    request,
                    "Başlanğıc tarixi bitiş tarixindən əvvəl olmalıdır.",
                    level=messages.ERROR
                )
                return HttpResponseRedirect('../date-range-summary/')
        except (ValueError, TypeError):
            self.message_user(
                request,
                "Tarix formatını yoxlayın.",
                level=messages.ERROR
            )
            return HttpResponseRedirect('../date-range-summary/')

        # Create the summary using the method defined below
        summary = self.create_date_range_summary(
            request.user, start_date, end_date)

        if summary:
            self.message_user(
                request,
                f"Tarix aralığı hesabatı uğurla yaradıldı: {start_date} - {end_date}",
                level=messages.SUCCESS
            )
            return HttpResponseRedirect(f'../{summary.id}/change/')
        else:
            self.message_user(
                request,
                "Bu tarix aralığında heç bir məlumat tapılmadı.",
                level=messages.WARNING
            )
            return HttpResponseRedirect('../date-range-summary/')

    def create_date_range_summary(self, user, start_date, end_date):
        """
        Create a summary for the given date range, gathering data from Orders
        and Statistics in that range.
        """
        start_datetime = timezone.make_aware(
            datetime.combine(start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(
            datetime.combine(end_date, datetime.max.time()))

        # Get orders in the date range
        orders = Order.objects.all_orders().filter(
            created_at__range=(start_datetime, end_datetime),
            is_paid=True
        )

        if not orders.exists():
            return None

        # Calculate totals
        # Get payments for these orders
        payments = Payment.objects.filter(orders__in=orders).distinct()

        # Calculate totals by payment type
        cash_total = Decimal('0.00')
        card_total = Decimal('0.00')
        other_total = Decimal('0.00')

        for payment in payments:
            # Check if payment has payment methods, otherwise use payment_type
            if payment.payment_methods.exists():
                # Use the new payment methods
                # Calculate change amount (assumed returned in cash)
                change_amount = payment.change or Decimal('0.00')

                for method in payment.payment_methods.all():
                    method_amount = method.amount

                    # If this is cash and there's change, subtract the change from cash
                    if method.payment_type == Payment.PaymentType.CASH and change_amount > 0:
                        method_amount = method_amount - change_amount
                        # Only subtract once from the first cash method
                        change_amount = Decimal('0.00')

                    if method.payment_type == Payment.PaymentType.CASH:
                        cash_total += method_amount
                    elif method.payment_type == Payment.PaymentType.CARD:
                        card_total += method_amount
                    elif method.payment_type == Payment.PaymentType.OTHER:
                        other_total += method_amount
            else:
                # Fallback to old payment_type field
                payment_amount = payment.final_price or Decimal('0.00')
                if payment.payment_type == Payment.PaymentType.CASH:
                    cash_total += payment_amount
                elif payment.payment_type == Payment.PaymentType.CARD:
                    card_total += payment_amount
                else:
                    other_total += payment_amount

        total = cash_total + card_total + other_total

        # Create the summary record
        summary = Summary.objects.create(
            start_date=start_date,
            end_date=end_date,
            cash_total=cash_total,
            card_total=card_total,
            other_total=other_total,
            total=total,
            created_by=user
        )

        # Link to relevant statistics
        statistics = Statistics.objects.filter(
            date__range=(start_date, end_date)
        )
        summary.statistics.set(statistics)

        return summary

    def print_summary_view(self, request, summary_id):
        """Print the summary report."""
        summary = self.get_object(request, summary_id)
        if not summary:
            self.message_user(request, "Hesabat tapılmadı.",
                              level=messages.ERROR)
            return HttpResponseRedirect('../../')

        success, msg = self.print_date_range_summary(summary, request.user)

        level = messages.SUCCESS if success else messages.ERROR
        self.message_user(request, msg, level=level)

        return HttpResponseRedirect('../change/')

    def preview_summary_view(self, request, summary_id):
        """Preview the summary report data as JSON."""
        summary = self.get_object(request, summary_id)
        if not summary:
            return JsonResponse({"error": "Hesabat tapılmadı"}, status=404)

        # Get the formatted preview data
        preview_data = self.get_summary_preview_data(summary)
        return JsonResponse(preview_data)

    def get_summary_preview_data(self, summary):
        """
        Generate the preview data for a summary, similar to what would be printed.
        """
        start_datetime = timezone.make_aware(
            datetime.combine(summary.start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(
            datetime.combine(summary.end_date, datetime.max.time()))

        # Get orders in the date range
        orders = Order.objects.all_orders().filter(
            created_at__range=(start_datetime, end_datetime),
            is_paid=True
        )

        # Get order items - group by category group, then by meal name
        order_items = OrderItem.objects.all_order_items().filter(order__in=orders).distinct()

        # Group items by category group, then aggregate by meal name
        grouped_items = {}

        for item in order_items.select_related("meal__category__group"):
            group_name = (
                item.meal.category.group.name
                if item.meal and item.meal.category and item.meal.category.group
                else "Digər"
            )

            # For extras, include the description in the meal name
            is_extra = item.meal.category.is_extra if item.meal and item.meal.category else False
            meal_name = item.meal.name

            # If it's an extra item with a description, append the description to the name
            if is_extra and item.description:
                meal_name = f"{meal_name} ({item.description})"

            quantity = item.quantity
            price = item.price / quantity  # Unit price

            # Initialize group if needed
            if group_name not in grouped_items:
                grouped_items[group_name] = {}

            # Initialize meal in group if needed
            if meal_name not in grouped_items[group_name]:
                grouped_items[group_name][meal_name] = {
                    "name": meal_name,
                    "qty": 0,
                    "price": round(float(price), 2),
                    "total": 0.0
                }

            # Update meal quantities and totals
            grouped_items[group_name][meal_name]["qty"] += quantity
            grouped_items[group_name][meal_name]["total"] = round(
                grouped_items[group_name][meal_name]["qty"] * grouped_items[group_name][meal_name]["price"], 2)

        # Convert nested dict to structured format
        groups_list = []
        grand_total_qty = 0
        grand_total_price = 0

        # Sort groups alphabetically
        for group_name in sorted(grouped_items.keys()):
            group_meals = grouped_items[group_name]

            # Convert meals dict to sorted list
            meals_list = list(group_meals.values())
            meals_list.sort(key=lambda x: x["name"])

            # Calculate group totals
            group_total_qty = sum(meal["qty"] for meal in meals_list)
            group_total_price = round(
                sum(meal["total"] for meal in meals_list), 2)

            # Add to grand totals
            grand_total_qty += group_total_qty
            grand_total_price += group_total_price

            # Add group to groups list
            groups_list.append({
                "name": group_name,
                "meals": meals_list,
                "total": {
                    "qty": group_total_qty,
                    "price": group_total_price
                }
            })

        # Get deleted order items from the OrderItemDeletionLog
        from apps.orders.models.order_deletion import OrderItemDeletionLog
        deleted_items = OrderItemDeletionLog.objects.filter(
            deleted_at__range=(start_datetime, end_datetime)
        )

        # Keep deleted items separate by meal name AND reason
        deleted_items_list = []

        for item in deleted_items:
            meal_name = item.meal_name
            # Check if this was an extra item by looking for parentheses in the name
            # For deleted items, we need to infer from the meal name since we don't have the meal object
            description = item.comment if item.comment else ""

            # If the description contains info about it being an extra, include it in the meal name
            if description and "extra" in description.lower():
                meal_name = f"{meal_name} ({description})"

            quantity = float(item.quantity)
            # Unit price rounded to 2 digits
            price = round(float(item.price / item.quantity), 2)
            total = round(float(item.price), 2)  # Total rounded to 2 digits
            reason = item.get_reason_display()
            deleted_by = item.deleted_by.get_full_name() if item.deleted_by else "Bilinmir"
            deleted_at = item.deleted_at.strftime('%d.%m.%Y %H:%M')

            # Find if we already have this meal with the same reason
            existing_item = next((
                i for i in deleted_items_list
                if i["name"] == meal_name and i["reason"] == reason
            ), None)

            if existing_item:
                # Update existing item
                existing_item["qty"] += quantity
                existing_item["total"] = round(
                    existing_item["price"] * existing_item["qty"], 2)
            else:
                # Add new item
                deleted_items_list.append({
                    "name": meal_name,
                    "qty": quantity,
                    "price": price,
                    "total": total,
                    "reason": reason,
                    "deleted_by": deleted_by,
                    "deleted_at": deleted_at
                })

        # Sort deleted items by name
        deleted_items_list.sort(key=lambda x: x["name"])

        # Calculate deleted totals
        deleted_total_qty = round(
            sum(item["qty"] for item in deleted_items_list), 2)
        deleted_total_price = round(
            sum(item["total"] for item in deleted_items_list), 2)

        # Use the summary payment totals which correctly account for discounts
        # These are taken from the Statistics models linked to this summary
        payment_totals = {
            "cash": round(float(summary.cash_total), 2),
            "card": round(float(summary.card_total), 2),
            "other": round(float(summary.other_total), 2),
            "total": round(float(summary.total), 2)
        }

        # Calculate total discount amount from payments
        discount_total = round(float(
            Payment.objects.filter(
                orders__in=orders
            ).aggregate(
                total=Sum('discount_amount')
            )['total'] or 0
        ), 2)

        payment_totals["discount"] = discount_total

        # Format the data for preview
        data = {
            "date_range": summary.date_range_display,
            "summary_id": summary.id,
            "created_by": summary.created_by.get_full_name() or summary.created_by.username,
            "created_at": summary.created_at.strftime('%d.%m.%Y %H:%M'),

            "items": groups_list,
            "grand_total": {
                "qty": grand_total_qty,
                "price": grand_total_price
            },

            "deleted_items": deleted_items_list,
            "deleted_total": {
                "qty": deleted_total_qty,
                "price": deleted_total_price
            },

            "payment_totals": payment_totals
        }

        return data

    def print_date_range_summary(self, summary, user=None):
        """
        Print the date range summary report, based on the PrinterService.print_order_items_summary method.
        """
        start_datetime = timezone.make_aware(
            datetime.combine(summary.start_date, datetime.min.time()))
        end_datetime = timezone.make_aware(
            datetime.combine(summary.end_date, datetime.max.time()))

        # Get orders in the date range
        orders = Order.objects.all_orders().filter(
            created_at__range=(start_datetime, end_datetime),
            is_paid=True
        )

        # Get order items
        order_items = OrderItem.objects.all_order_items().filter(order__in=orders).distinct()

        width = 48
        lines = []
        lines.append("=" * width)
        lines.append("ÜMUMİ HESABAT".center(width))
        lines.append("=" * width)
        lines.append(f"Hesabat ID: {summary.id}")
        lines.append(f"Tarix aralığı: {summary.date_range_display}")
        lines.append(f"Tarix: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        if user:
            lines.append(
                f"Istifadəçi: {user.get_full_name() or user.username}")
        lines.append("-" * width)

        # Group active items first by MealGroup, then by Meal name
        grouped = {}
        for item in order_items.select_related("meal__category__group"):
            group_name = (
                item.meal.category.group.name
                if item.meal and item.meal.category and item.meal.category.group
                else "Digər"
            )

            # For extras, include the description in the meal name
            is_extra = item.meal.category.is_extra if item.meal and item.meal.category else False
            meal_name = item.meal.name

            # If it's an extra item with a description, append the description to the name
            if is_extra and item.description:
                meal_name = f"{meal_name} ({item.description})"

            grouped.setdefault(group_name, {})
            agg = grouped[group_name].setdefault(
                meal_name, {"qty": 0, "total": Decimal("0.00")})
            agg["qty"] += item.quantity
            agg["total"] += item.price

        grand_total_qty = 0
        grand_total_price = Decimal("0.00")

        for group, meals in grouped.items():
            lines.append(f"\n*** {group.upper()} ***")
            lines.append(f"{'Məhsul':<25}{'Miqdar':>6}{'Cəm':>15}")

            group_qty = 0
            group_price = Decimal("0.00")
            for meal_name, agg in meals.items():
                qty = agg["qty"]
                total = agg["total"]
                lines.append(f"{meal_name[:25]:<25}{qty:>6}{total:>15.2f}")
                group_qty += qty
                group_price += total

            lines.append(
                f"{'Qrup cəmi:':<25}{group_qty:>6}{group_price:>15.2f}")
            lines.append("-" * width)

            grand_total_qty += group_qty
            grand_total_price += group_price

        lines.append(
            f"{'CƏMİ':<25}{grand_total_qty:>6}{grand_total_price:>15.2f}")
        lines.append("=" * width)

        # Add payment type totals
        lines.append("\n" + "ÖDƏMƏ NÖVÜNƏ GÖRƏ".center(width))
        lines.append(f"{'Nağd':<25}{' ':>6}{summary.cash_total:>15.2f}")
        lines.append(f"{'Kart':<25}{' ':>6}{summary.card_total:>15.2f}")
        lines.append(f"{'Digər':<25}{' ':>6}{summary.other_total:>15.2f}")

        # Calculate and add discount total
        discount_total = Payment.objects.filter(
            orders__in=orders
        ).aggregate(
            total=Sum('discount_amount')
        )['total'] or 0

        lines.append(f"{'Endirim':<25}{' ':>6}{discount_total:>15.2f}")

        lines.append("-" * width)
        lines.append(f"{'CƏMİ':<25}{' ':>6}{summary.total:>15.2f}")

        lines.append("\n" + "=" * width)
        lines.append("BÜTÜN MƏBLƏĞLƏR MANATLA".center(width))
        lines.append("=" * width)
        lines.append("\n\n\n")

        text = "\n".join(lines)
        response = PrinterService._send_text_to_main_printer(
            text,
            payment=None,
            type=Receipt.ReceiptType.ORDER_SUMMARY
        )

        return (response.status_code == 200), (
            "Hesabat uğurla çap edildi."
            if response.status_code == 200
            else "Çap alınmadı."
        )
