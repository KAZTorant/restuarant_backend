import socket
from datetime import datetime
from apps.orders.models import Statistics
from apps.orders.models.order import Order
from apps.printers.models import Receipt
from apps.tables.models import Table
from apps.printers.models import Printer

from django.db.models import Sum

from apps.payments.models.pay_table_orders import Payment


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
                is_deleted=True).filter(is_paid=False)
            if not orders.exists():
                return False, "Sifariş mövcud deyil."

            receipt_data = PrinterService._build_receipt_data(
                table, orders, is_paid, payment_type,
                discount_amount, discount_comment, paid_amount, change
            )

            formatted_text = PrinterService._format_customer_receipt(
                receipt_data)
            response = PrinterService._send_text_to_main_printer(
                formatted_text)

            if response.status_code == 200:
                orders.update(is_check_printed=True)
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
    def _build_receipt_data(table, orders, is_paid, payment_type, discount_amount, discount_comment, paid_amount, change):
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
        lines.append("CAFEPARK".center(width))
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
        if data['payment_type']:
            lines.append(f"Ödəniş növü: {data['payment_type'].capitalize()}")

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
