import socket
from datetime import datetime
from apps.orders.models import Statistics
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
        items = []
        total = 0
        for item in order.order_items.all():
            line_total = item.quantity * item.meal.price
            items.append({
                'name': item.meal.name,
                'quantity': item.quantity,
                'price': item.meal.price,
                'line_total': line_total
            })
            total += line_total
        return {
            'order_id': order.id,
            'items': items,
            'order_total': total
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
            for item in order['items']:
                lines.append(
                    f"{item['quantity']}x {item['name']:<16}{item['line_total']:>8.2f} AZN")
            lines.append(f"Cəmi: {order['order_total']:>17.2f} AZN")
            lines.append("-" * width)

        lines.append(f"Ümumi məbləğ: {data['total']:>29.2f} AZN")
        if data['discount']:
            lines.append(f"Endirim: {data['discount']:>33.2f} AZN")
            if data['discount_comment']:
                lines.append(f"Qeyd: {data['discount_comment']}")
        lines.append(f"Yekun məbləğ: {data['final_total']:>27.2f} AZN")
        if data['paid_amount']:
            lines.append(f"Ödənildi: {data['paid_amount']:>30.2f} AZN")
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
        width = 48
        lines = []

        lines.append("=" * width)
        lines.append("HAZIRLANMA ÇEKİ".center(width))
        lines.append("=" * width)
        lines.append(f"Tarix: {data['date']}")
        lines.append(
            f"Masa: {data['table']['room']} - {data['table']['number']}")
        if data['orders']:
            lines.append(f"Sifariş №: {data['orders'][0]['order_id']}")
        else:
            lines.append("Sifariş №: N/A")
        lines.append("-" * width)

        for order in data['orders']:
            lines.append(f"Sifariş #{order['order_id']}")
            for item in order['items']:
                lines.append(f"{item['quantity']}x {item['name']}")
            lines.append("-" * width)

        lines.append("Zəhmət olmasa sifarişi düzgün hazırlayın!")
        lines.append("=" * width)
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
        try:
            with socket.create_connection((ip_address, port), timeout=5) as s:
                s.sendall(text.encode('cp857', errors='replace') + ESC_CUT)
            return DummyResponse(200)
        except Exception as e:
            print(f"Printerə data göndərilərkən xəta: {e}")
            return DummyResponse(500)

    @staticmethod
    def print_shift_summary(stat_id, user=None):
        """
        Prints the shift summary for the Statistics record with pk=stat_id.
        """
        # 1) Load the stat record
        try:
            stat = Statistics.objects.get(pk=stat_id)
        except Statistics.DoesNotExist:
            return False, f"Statistika id={stat_id} tapılmadı."

        orders_qs = stat.orders.all_orders()
        if not orders_qs.exists():
            return False, "Bu statistikada heç bir sifariş yoxdur."

        width = 48
        lines = []

        # Header
        lines.append(f"{stat.id:03d} Z-Hesabat")
        main_printer = Printer.objects.filter(is_main=True).first()
        terminal = main_printer.name if main_printer else "N/A"
        lines.append(f"Terminal: {terminal}")
        lines.append(f"Kassa növbəsi: {stat.id}")
        lines.append(
            f"Status: {'Təsdiqləndi' if stat.is_z_checked else 'Təsdiqlənməmiş'}"
        )

        # Shift open time = earliest order.created_at
        first_order = orders_qs.order_by("created_at").first()
        opened = first_order.created_at.strftime(
            "%d.%m.%Y %H:%M") if first_order else "–"
        lines.append(f"Növbə açıldığı: {opened}")

        # Current time & user
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        lines.append(f"Cari vaxt:       {now}")
        if user:
            try:
                name = user.get_full_name() or user.username
            except:
                name = str(user)
            lines.append(f"Cari istifadəçi: {name}")

        lines.append("-" * width)

        # 2) Aggregate cash vs. card, **via** Payments linked to these orders
        cash = (
            Payment.objects
            .filter(payment_type=Payment.PaymentType.CASH, orders__in=orders_qs)
            .distinct()
            .aggregate(total=Sum("paid_amount"))["total"] or 0
        )
        card = (
            Payment.objects
            .filter(payment_type=Payment.PaymentType.CARD, orders__in=orders_qs)
            .distinct()
            .aggregate(total=Sum("paid_amount"))["total"] or 0
        )
        other = (
            Payment.objects
            .filter(payment_type=Payment.PaymentType.OTHER, orders__in=orders_qs)
            .distinct()
            .aggregate(total=Sum("paid_amount"))["total"] or 0
        )

        lines.append("Satışlar")
        lines.append(f"Nağd ödəniş    {cash:>10.2f}")
        lines.append(f"Bank kartları  {card:>10.2f}")
        lines.append(f"Digər  {other:>10.2f}")
        lines.append(f"CƏMİ (Satışlar): {(cash + card + other):>10.2f}")

        # Footer
        lines.append("=" * width)
        lines.append("BÜTÜN MƏBLƏĞLƏR MANATLA")
        lines.append("=" * width)
        lines.append("\n\n\n")

        text = "\n".join(lines)

        # 3) Send to main printer
        response = PrinterService._send_text_to_main_printer(
            text, payment=None, type=Receipt.ReceiptType.Z_SUMMRY
        )

        if response.status_code == 200:
            return True, "Növbə yekunu uğurla çap edildi."
        return False, "Printerə qoşulmaq mümkün olmadı."
