import socket
from datetime import datetime
from apps.orders.models import Statistics
from apps.orders.models.order import Order
from apps.printers.models import Receipt
from apps.tables.models import Table
from apps.printers.models import Printer

from django.db.models import Sum

from apps.payments.models.pay_table_orders import Payment, PaymentMethod


class DummyResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class PrinterService:

    # ========================= #
    #   CORE PUBLIC ENTRYPOINT #
    # ========================= #

    @staticmethod
    def print_orders_for_table(
        table_id,
        is_paid=False,
        force_print=False,
        payment_type=None,
        payment_methods=None,
        discount_amount=0,
        discount_comment="",
        paid_amount=0,
        change=0
    ):
        try:
            table = Table.objects.get(pk=table_id)
            if not table.can_print_check() and not force_print:
                return False, "Aktiv sifariş yoxdur və ya çek artıq çap edilib."

            orders = table.orders.exclude(
                is_deleted=True
            ).filter(is_paid=False)

            if not orders.exists():
                return False, "Sifariş mövcud deyil."

            receipt_data = PrinterService._build_receipt_data(
                table, orders, is_paid, payment_type, payment_methods,
                discount_amount, discount_comment, paid_amount, change
            )

            formatted_text = PrinterService._format_customer_receipt(
                receipt_data
            )
            response = PrinterService._send_text_to_main_printer(
                formatted_text
            )

            if response.status_code == 200:
                if not is_paid:
                    for o in orders:
                        o.is_check_printed = True
                        o.save()
                # orders.update(is_check_printed=True)
                return True, "Çek uğurla çap edildi."
            return False, "Çek çap edilə bilmədi. Printer qoşulmayıb."

        except Table.DoesNotExist:
            return False, "Masa mövcud deyil."

    @staticmethod
    def send_to_worker_printer(receipt_data, worker_printer, orders=None):
        try:
            formatted_text = PrinterService._format_worker_receipt(
                receipt_data
            )

            response = PrinterService._send_text_to_printer(
                formatted_text,
                worker_printer.ip_address,
                worker_printer.port,
            )

            receipt = Receipt.objects.create(
                type=Receipt.ReceiptType.PREPERATION_PLACE,
                text=formatted_text,
                printer_response_status_code=response.status_code,

            )
            if orders:
                receipt.orders.set(orders)

            return response
        except Exception as e:
            print(f"İşçi printerinə data göndərilərkən xəta: {e}")
            return DummyResponse(500)

    # ============================= #
    #   DATA BUILDING & PARSING    #
    # ============================= #

    @staticmethod
    def _build_receipt_data(table, orders, is_paid, payment_type, payment_methods, discount_amount, discount_comment, paid_amount, change):
        order_data = []
        waitress = table.waitress
        total = 0

        for order in orders:
            parsed = PrinterService._parse_order(order)
            order_data.append(parsed)
            total += parsed["order_total"]

        final_total = max(total - discount_amount, 0)

        return {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "table": {
                "room": table.room.name if table.room else "N/A",
                "number": table.number
            },
            "orders": order_data,
            "waitress": waitress.get_full_name() if waitress else "N/A",
            "total": total,
            "final_total": final_total,
            "discount": discount_amount,
            "discount_comment": discount_comment,
            "paid_amount": paid_amount,
            "change": change,
            "payment_type": payment_type,
            "payment_methods": payment_methods,
            "is_paid": is_paid
        }

    @staticmethod
    def _parse_order(order):
        """
        Parse an order into grouped items, aggregating quantities and comments.
        """

        meal_groups = {}

        # Group items by meal (and by item ID if it's an extra)
        for item in order.order_items.all():
            if item.meal.is_extra:
                mid = f'{item.meal.id}_{item.id}'
                name = f"{item.meal.name}: {item.description}"
                price = item.price or 0
            else:
                mid = item.meal.id
                name = item.meal.name
                price = item.meal.price or 0

            if mid not in meal_groups:
                meal_groups[mid] = {
                    "name":       name,
                    "quantity":   0,
                    "price":      price,
                    "line_total": 0,
                    "comments":   set(),  # use set to avoid duplicates
                }
            grp = meal_groups[mid]
            grp["quantity"] += item.quantity

            # collect any non-empty comment
            comment = getattr(item, "comment", None)
            if comment and comment.strip():
                grp["comments"].add(comment.strip())

        # Finalize groups
        grouped_items = []
        for grp in meal_groups.values():
            grp["line_total"] = grp["quantity"] * grp["price"]
            grp["comments"] = sorted(grp["comments"])
            grouped_items.append(grp)

        # Calculate order total
        order_total = sum(item["line_total"] for item in grouped_items)

        return {
            "order_id": order.id,
            "items": grouped_items,
            "order_total": order_total
        }

    # ========================= #
    #   FORMATTING FUNCTIONS   #
    # ========================= #

    @staticmethod
    def _format_customer_receipt(data):
        width = 48
        lines = []

        lines.append("=" * width)
        lines.append("CAFEPARK TAVERN".center(width))
        lines.append("=" * width)

        lines.append(f"Tarix: {data['date']}")
        lines.append(
            f"Masa: {data['table']['room']} - {data['table']['number']}")
        lines.append(f"Ofisiant: {data['waitress']}")
        lines.append("-" * width)

        for order in data['orders']:
            lines.append(f"Sifariş #{order['order_id']}")
            lines.append(f"{'Ad':<19}{'Miqdar':>5}{'Qiymət':>9}{'Cəm':>13}")
            lines.append("-" * width)

            for item in order['items']:
                lines.append(
                    f"{item['name']:<19}{item['quantity']:>5}{item['price']:>9.2f} {item['line_total']:>10.2f} AZN"
                )

            lines.append("-" * width)
            lines.append(f"Cəmi: {order['order_total']:>37.2f} AZN")
            lines.append("-" * width)

        lines.append(f"Ümumi məbləğ: {data['total']:>28.2f} AZN")
        if data['discount']:
            lines.append(f"Endirim: {data['discount']:>28.2f} AZN")
            if data['discount_comment']:
                lines.append(f"Qeyd: {data['discount_comment']}")
        lines.append(f"Yekun məbləğ: {data['final_total']:>28.2f} AZN")
        if data['paid_amount']:
            lines.append(f"Ödənildi: {data['paid_amount']:>28.2f} AZN")
        if data['change']:
            lines.append(f"Qaytarıldı: {data['change']:>28.2f} AZN")

        # Handle payment methods
        if data['payment_methods']:
            lines.append("-" * width)
            lines.append("Ödəniş növləri:")
            for method in data['payment_methods']:
                payment_type = PaymentMethod.PaymentType(
                    method['payment_type']).label
                amount = float(method['amount'])
                lines.append(f"{payment_type}: {amount:>32.2f} AZN")
        elif data['payment_type']:
            payment_type = PaymentMethod.PaymentType(
                data['payment_type']).label
            lines.append(f"Ödəniş növü: {payment_type}")

        lines.append("=" * width)
        lines.append("Bizi seçdiyiniz üçün təşəkkür edirik!")
        lines.append("=" * width)
        lines.append("\n\n\n")

        return "\n".join(lines)

    @staticmethod
    def _format_worker_receipt(data):
        """
        Format a worker (preparation) receipt with a table-like structure
        and enlarged font (medium-large size).
        """

        ESC = '\x1B'
        GS = '\x1D'
        MEDIUM_LARGE_SIZE = GS + '!' + '\x10'  # 2x height only
        NORMAL_SIZE = GS + '!' + '\x00'
        width = 48

        lines = []

        lines.append(MEDIUM_LARGE_SIZE)
        lines.append('=' * width)
        lines.append('HAZIRLANMA ÇƏKİ'.center(width))
        lines.append('=' * width)

        lines.append(f"Tarix: {data['date']}")
        lines.append(
            f"Masa: {data['table']['room']} - {data['table']['number']}")
        order_ids = [str(o['order_id']) for o in data['orders']]
        lines.append(f"Sifariş №: {', '.join(order_ids)}")
        lines.append('-' * width)

        for order in data['orders']:
            lines.append(f"Sifariş #{order['order_id']}")
            lines.append(f"{'Ad':<30}{'Miqdar':>6}")
            lines.append('-' * width)

            for item in order['items']:
                lines.append(f"{item['name']:<30}{item['quantity']:>6}")
                for comment in item.get('comments', []):
                    lines.append(f"  Qeyd: {comment}")

            lines.append('-' * width)

        lines.append("Zəhmət olmasa sifarişi düzgün hazırlayın!")
        lines.append('=' * width)

        lines.append(NORMAL_SIZE)
        lines.append("\n\n\n")

        return "\n".join(lines)

    # ========================= #
    #     PRINTER HANDLERS     #
    # ========================= #

    @staticmethod
    def _send_text_to_main_printer(text, payment=None, type=Receipt.ReceiptType.CUSTOMER):
        printer = Printer.objects.filter(is_main=True).first()
        if not printer:
            raise Exception("Sistemdə əsas printer təyin edilməyib.")

        response = PrinterService._send_text_to_printer(
            text, printer.ip_address, printer.port
        )

        Receipt.objects.create(
            type=type,
            text=text,
            payment=payment,
            printer_response_status_code=response.status_code,
        )

        return response

    @staticmethod
    def _send_text_to_printer(text, ip_address, port):
        ESC_CUT = b'\x1D\x56\x00'
        BEEP = b'\x1B\x42\x03\x02'  # Beep 3 times, 200ms each

        mapped = PrinterService.mapping(text)
        try:
            with socket.create_connection((ip_address, port), timeout=5) as s:
                s.sendall(mapped.encode(
                    'cp857', errors='replace') + ESC_CUT + BEEP)
            return DummyResponse(200)
        except Exception as e:
            print(f"Printerə data göndərilərkən xəta: {e}")
            return DummyResponse(500)

    @staticmethod
    def mapping(text: str) -> str:
        """
        Map Azerbaijani-specific characters to ASCII equivalents:
          ə→e, Ə→E, ı→i, İ→I, ö→o, Ö→O,
          ü→u, Ü→U, ğ→g, Ğ→G, ş→s, Ş→S, ç→c, Ç→C
        """
        char_map = {
            'ə': 'e', 'Ə': 'E',
            'ı': 'i', 'İ': 'I',
            'ö': 'o', 'Ö': 'O',
            'ü': 'u', 'Ü': 'U',
            'ğ': 'g', 'Ğ': 'G',
            'ş': 's', 'Ş': 'S',
            'ç': 'c', 'Ç': 'C',
        }
        for src, dst in char_map.items():
            text = text.replace(src, dst)
        return text

    @staticmethod
    def print_shift_summary(stat_id, user=None):
        try:
            stat = Statistics.objects.get(pk=stat_id)
        except Statistics.DoesNotExist:
            return False, f"Statistika id={stat_id} tapılmadı."

        cash = stat.cash_total
        card = stat.card_total
        other = stat.other_total
        open_sum = Order.objects.filter(is_paid=False).aggregate(
            total=Sum('total_price'))['total'] or 0

        width = 48
        lines = []

        lines.append("=" * width)
        lines.append("NÖVBƏ YEKUNU".center(width))
        lines.append("=" * width)

        main_printer = Printer.objects.filter(is_main=True).first()
        terminal = main_printer.name if main_printer else "N/A"
        lines.append(f"Terminal: {terminal}")
        lines.append(f"Kassa növbəsi: {stat.id}")
        lines.append(
            f"Status: {'Təsdiqlənib' if stat.is_closed else 'Qaralama'}")
        lines.append(
            f"Növbə açıldı: {stat.start_time.strftime('%d.%m.%Y %H:%M')}")
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        lines.append(f"Cari vaxt: {now}")
        if user:
            name = user.get_full_name() or user.username
            lines.append(f"Cari istifadəçi: {name}")
        lines.append("-" * width)

        lines.append(f"{'Satışlar':<30}{''}")
        lines.append(f"{'Nağd ödəniş':<30}{cash:>15.2f}")
        lines.append(f"{'Bank kartları':<30}{card:>15.2f}")
        lines.append(f"{'Digər ödənişlər':<30}{other:>15.2f}")
        lines.append(f"{'CƏMİ (Satışlar)':<30}{(cash + card + other):>15.2f}")
        lines.append("-" * width)

        lines.append(f"{'Silinmələr':<30}{''}")
        lines.append(f"{'Müəssisə hesabına':<30}{0.00:>15.2f}")
        lines.append(f"{'Məhsulların silinməsi':<30}{0.00:>15.2f}")
        lines.append(f"{'CƏMİ (Silinmələr)':<30}{0.00:>15.2f}")
        lines.append("-" * width)

        lines.append(f"{'Açıq sifarişlər':<30}{open_sum:>15.2f}")
        lines.append("-" * width)

        lines.append(f"{'Nağd vasitələr hərəkəti':<30}")
        lines.append(
            f"{'Növbənin evvəlində kassada':<30}{stat.initial_cash:>15.2f}")
        lines.append(f"{'+ Nağd satışlar':<30}{cash:>15.2f}")
        lines.append(f"{'- Qaytarılan nağd pullar':<30}{0.00:>15.2f}")
        lines.append(
            f"{'= Kassada olmalıdır':<30}{stat.remaining_cash:>15.2f}")
        lines.append("=" * width)

        lines.append("DİGƏR ÖDƏNİŞ NÖVLƏRİ".center(width))
        lines.append("=" * width)

        lines.append(f"{'Nağd ödəniş':<30}{cash:>15.2f}")
        lines.append(f"{'Bank kartları':<30}{card:>15.2f}")
        lines.append("=" * width)
        lines.append("BÜTÜN MƏBLƏĞLƏR MANATLA".center(width))
        lines.append("=" * width)
        lines.append("\n\n\n")

        text = "\n".join(lines)

        response = PrinterService._send_text_to_main_printer(
            text,
            payment=None,
            type=Receipt.ReceiptType.SHIFT_SUMMARY
        )

        if response.status_code == 200:
            return True, "Növbə yekunu uğurla çap edildi."
        return False, "Printerə qoşulmaq mümkün olmadı."

    @staticmethod
    def print_z_hesabat(stat_id, user=None):
        try:
            stat = Statistics.objects.get(pk=stat_id)
        except Statistics.DoesNotExist:
            return False, f"Statistika id={stat_id} tapılmadı."

        cash = stat.cash_total
        card = stat.card_total
        other = stat.other_total
        total = cash + card + other

        op_count = stat.orders.count()
        open_sum = Order.objects.filter(is_paid=False).aggregate(
            total=Sum('total_price'))['total'] or 0

        width = 48
        lines = []

        lines.append("=" * width)
        lines.append("Z-HESABAT".center(width))
        lines.append("=" * width)

        main_printer = Printer.objects.filter(is_main=True).first()
        term = main_printer.name if main_printer else "N/A"
        lines.append(f"Terminal: {term}")
        lines.append(f"Kassa növbəsi: {stat.id}")
        lines.append(
            f"Status: {'Təsdiqlənib' if stat.is_z_checked else 'Qaralama'}")
        lines.append(
            f"Növbə açıldı: {stat.start_time.strftime('%d.%m.%Y %H:%M')}")
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        lines.append(f"Cari vaxt: {now}")
        if user:
            name = user.get_full_name() or user.username
            lines.append(f"Cari istifadəçi: {name}")
        lines.append("-" * width)

        lines.append(f"{'Nağd Satış':<30}{cash:>15.2f}")
        lines.append(f"{'Qaytarılma':<30}{0.00:>15.2f}")
        lines.append(f"{'Alış':<30}{0.00:>15.2f}")
        lines.append(f"{'Alış qaytarılması':<30}{0.00:>15.2f}")
        lines.append("-" * width)

        lines.append(f"{'Bank kartı Satış':<30}{card:>15.2f}")
        lines.append(f"{'Bank kartı Qaytarılma':<30}{0.00:>15.2f}")
        lines.append("-" * width)

        lines.append(f"{'CƏMİ':<30}{total:>15.2f}")
        lines.append("-" * width)

        lines.append(f"{'Açıq sifarişlər':<30}{open_sum:>15.2f}")
        lines.append("-" * width)

        lines.append(f"{'YERİNƏ YETİRİLƏN ƏMƏLİYYATLAR':<30}{op_count}")
        lines.append("-" * width)

        lines.append("Diqqət! Göstərilən məbləğlər fiskal registr...")
        lines.append("=" * width)
        lines.append("\n\n\n")

        text = "\n".join(lines)

        response = PrinterService._send_text_to_main_printer(
            text,
            payment=None,
            type=Receipt.ReceiptType.Z_SUMMRY
        )

        if response.status_code == 200:
            return True, "Z-hesabat uğurla çap edildi."
        return False, "Printerə qoşulmaq mümkün olmadı."

    @staticmethod
    def print_order_items_summary(stat_id, user=None):
        from decimal import Decimal
        from datetime import datetime
        from django.db.models import Min
        from django.utils import timezone
        from apps.orders.models.order import OrderItem
        from apps.orders.models.order_deletion import OrderItemDeletionLog

        try:
            stat = Statistics.objects.get(pk=stat_id)
        except Statistics.DoesNotExist:
            return False, f"Statistika id={stat_id} tapılmadı."

        orders = Order.objects.all_orders().filter(statistics=stat)
        order_items = OrderItem.objects.all_order_items().filter(order__in=orders).distinct()

        # Determine actual shift time range
        order_dates = orders.aggregate(earliest=Min('created_at'))
        shift_start = order_dates['earliest']
        shift_end = stat.end_time or timezone.now()

        deleted_items = OrderItemDeletionLog.objects.filter(
            deleted_at__range=(shift_start, shift_end)
        )

        width = 48
        lines = []
        lines.append("=" * width)
        lines.append("SATILMIŞ MƏHSULLAR".center(width))
        lines.append("=" * width)
        lines.append(f"Kassa növbəsi: {stat.id}")
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
            meal_name = item.meal.name
            grouped.setdefault(group_name, {})
            agg = grouped[group_name].setdefault(
                meal_name, {"qty": 0, "total": Decimal("0.00")})
            agg["qty"] += item.quantity
            agg["total"] += item.quantity * item.price

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

        # Append deleted items summary (unchanged logic, but also sums per meal)
        if deleted_items.exists():
            lines.append("\n" + "SİLİNMİŞ MƏHSULLAR".center(width))
            reasons = {
                OrderItemDeletionLog.REASON_RETURN: "Anbara Qaytarma",
                OrderItemDeletionLog.REASON_WASTE: "Tullantı"
            }

            for reason_code, reason_label in reasons.items():
                reason_group = deleted_items.filter(reason=reason_code)
                if not reason_group.exists():
                    continue

                # aggregate per meal_name
                deleted_agg = {}
                for item in reason_group:
                    deleted_agg.setdefault(
                        item.meal_name, {"qty": 0, "total": Decimal("0.00")})
                    deleted_agg[item.meal_name]["qty"] += int(item.quantity)
                    deleted_agg[item.meal_name]["total"] += item.quantity * item.price

                lines.append(f"\n*** {reason_label.upper()} ***")
                lines.append(f"{'Məhsul':<25}{'Miqdar':>6}{'Cəm':>15}")

                reason_qty = 0
                reason_price = Decimal("0.00")
                for meal_name, agg in deleted_agg.items():
                    qty = agg["qty"]
                    total = agg["total"]
                    lines.append(f"{meal_name[:25]:<25}{qty:>6}{total:>15.2f}")
                    reason_qty += qty
                    reason_price += total

                lines.append(
                    f"{'Cəmi:':<25}{reason_qty:>6}{reason_price:>15.2f}")
                lines.append("-" * width)

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
            "Məhsullar qrupla çap edildi."
            if response.status_code == 200
            else "Çap alınmadı."
        )

    @staticmethod
    def send_deletion_receipt(receipt_data, worker_printer):
        """
        New entrypoint for printing deletion receipts.
        """
        try:
            formatted = PrinterService._format_deletion_receipt(receipt_data)
            resp = PrinterService._send_text_to_printer(formatted,
                                                        worker_printer.ip_address,
                                                        worker_printer.port)
            Receipt.objects.create(
                type=Receipt.ReceiptType.PREPERATION_PLACE,
                text=formatted,
                printer_response_status_code=resp.status_code,
            )
            return resp
        except Exception as e:
            print(f"Silinmə cekini printerə göndərərkən xəta: {e}")
            return DummyResponse(500)

    @staticmethod
    def _format_deletion_receipt(data):
        """
        Builds a clear, tabular receipt for removed items,
        showing name, qty, reason, who deleted and comments.
        """
        ESC = '\x1B'
        GS = '\x1D'
        MED = GS + '!' + '\x10'  # large
        NORM = GS + '!' + '\x00'
        width = 48

        lines = []
        lines.append(MED)
        lines.append('=' * width)
        lines.append('SİLİNƏN MƏHSUL ÇƏKİ'.center(width))
        lines.append('=' * width)
        lines.append(f"Tarix: {data['date']}")
        lines.append(
            f"Masa: {data['table']['room']} - {data['table']['number']}")
        lines.append(f"Ofisiant: {data['waitress']}")
        lines.append('-' * width)

        for order in data['orders']:
            lines.append(f"Sifariş #{order['order_id']}")
            lines.append(f"{'Ad':<20}{'Miqdar':>6}{'Səbəb':>10}")
            lines.append('-' * width)
            for item in order['items']:
                # main row: name, qty, reason
                lines.append(
                    f"{item['name']:<20}{item['quantity']:>6}{item['reason']:<10}")
                # who deleted & customer no.
                lines.append(
                    f"Silən: {item['deleted_by']}  Müştəri№: {item['customer_number']}")
                if item['comment']:
                    lines.append(f"Qeyd: {item['comment']}")
                lines.append('-' * width)

        lines.append(NORM)
        lines.append("\n\n\n")
        return "\n".join(lines)
