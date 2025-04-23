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
        items = []
        total = 0
        for item in order.order_items.all():
            line_total = item.quantity * item.meal.price
            comment = getattr(item, 'comment', '').strip() or None
            items.append({
                'name': item.meal.name,
                'quantity': item.quantity,
                'price': item.meal.price,
                'line_total': line_total,
                'comment': comment,
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
        """
        Format a worker (preparation) receipt with enlarged font
        and unique comments for each meal-group.
        """

        # ESC/POS commands for double width & height
        ESC = '\x1B'
        DOUBLE_SIZE = ESC + '!\x11'
        NORMAL_SIZE = ESC + '!\x00'
        width = 48
        lines = []

        # Header in double size
        lines.append(DOUBLE_SIZE + '=' * width + NORMAL_SIZE)
        lines.append(
            DOUBLE_SIZE + 'HAZIRLANMA ÇEKİ'.center(width) + NORMAL_SIZE)
        lines.append(DOUBLE_SIZE + '=' * width + NORMAL_SIZE)
        lines.append(f"Tarix: {data['date']}")
        lines.append(
            f"Masa: {data['table']['room']} - {data['table']['number']}")
        order_ids = [str(o['order_id']) for o in data['orders']]
        lines.append(f"Sifariş №: {', '.join(order_ids)}")
        lines.append('-' * width)

        # There may be just one grouped order in data['orders']
        for order in data['orders']:
            # Print each meal-group and its own comments
            for item in order['items']:
                # Meal line
                lines.append(f"{item['quantity']}x {item['name']}")
                # Now, if this group has comments, print each in double size
                for comment in item.get('comments', []):
                    lines.append(
                        DOUBLE_SIZE + f"  Qeyd: {comment}" + NORMAL_SIZE
                    )
            lines.append('-' * width)

        lines.append("Zəhmət olmasa sifarişi düzgün hazırlayın!")
        lines.append(DOUBLE_SIZE + '=' * width + NORMAL_SIZE)
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
        mapped = PrinterService.mapping(text)
        try:
            with socket.create_connection((ip_address, port), timeout=5) as s:
                s.sendall(mapped.encode('cp857', errors='replace') + ESC_CUT)
            return DummyResponse(200)
        except Exception as e:
            print(f"Printerə data göndərilərkən xəta: {e}")
            return DummyResponse(500)

    @staticmethod
    def print_shift_summary(stat_id, user=None):
        """
        Fetch the Statistics record (assumed already up‑to‑date),
        format every field into a Z‑check layout, and send it to the main printer.
        """
        # 1) Load the shift record
        try:
            stat = Statistics.objects.get(pk=stat_id)
        except Statistics.DoesNotExist:
            return False, f"Statistika id={stat_id} tapılmadı."

        # 2) Read pre‑computed totals straight from the model
        cash = stat.cash_total
        card = stat.card_total
        other = stat.other_total

        # 3) Sum of any open (unpaid) orders across the system
        open_sum = (Order.objects
                         .filter(is_paid=False)
                         .aggregate(total=Sum('total_price'))['total']
                    ) or 0

        # 4) Build the receipt text
        width = 48
        lines = []

        # — Header
        lines.append(f"Növbə yekunu")
        main_printer = Printer.objects.filter(is_main=True).first()
        terminal = main_printer.name if main_printer else "N/A"
        lines.append(f"Terminal: {terminal}")
        lines.append(f"Kassa növbəsi: {stat.id}")
        lines.append(
            f"Status: {'Təsdiqlənib' if stat.is_closed else 'Qaralama'}"
        )
        lines.append(
            f"Növbə açıldığı: {stat.start_time.strftime('%d.%m.%Y %H:%M')}")
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        lines.append(f"Cari vaxt:       {now}")
        if user:
            name = user.get_full_name() or user.username
            lines.append(f"Cari istifadəçi: {name}")
        lines.append("-" * width)

        # — Sales totals
        lines.append("Satışlar")
        lines.append(f"Nağd ödəniş    {cash:>10.2f}")
        lines.append(f"Bank kartları  {card:>10.2f}")
        lines.append(f"Digər ödənişlər {other:>10.2f}")
        lines.append(f"CƏMİ (Satışlar): {(cash + card + other):>10.2f}")
        lines.append("")

        # — Voids (hard‑coded zeros unless you track them)
        lines.append("Silinmələr")
        lines.append(f"Müəssisə hesabına      0,00")
        lines.append(f"Məhsulların silinməsi  0,00")
        lines.append(f"CƏMİ (Silinmələr):     0,00")
        lines.append("")

        # — Open orders
        lines.append(f"Açıq sifarişlər        {open_sum:.2f}")
        lines.append("")

        # — Cash‑drawer movements
        lines.append("Nağd vasitələrin hərəkəti")
        lines.append(
            f"Növbənin əvvəlində kassada nəğd pul:   {stat.initial_cash:.2f}")
        lines.append("")
        lines.append(f"+ nağd satışlar         {stat.cash_total:.2f}")
        lines.append(f"− qaytarılan nağd pullar 0,00")
        lines.append(f"= kassada olmalıdır      {stat.remaining_cash:.2f}")
        lines.append("")

        # — Other payment‑type breakdown
        lines.append("=" * width)
        lines.append("DİGƏR ÖDƏNİŞ NÖVLƏRİ")
        lines.append("=" * width)

        lines.append("Nağd ödəniş")
        lines.append(f"Nağd                    —          {cash:.2f}")
        lines.append(f"CƏMİ (Nağd):                        {cash:.2f}")
        lines.append("")
        lines.append("Bank kartları")
        lines.append(f"Bank kartları           —          {card:.2f}")
        lines.append(f"CƏMİ (Bank kartları):               {card:.2f}")
        lines.append("")
        lines.append("BÜTÜN MƏBLƏĞLƏR MANATLA")
        lines.append("=" * width)
        lines.append("\n\n\n")

        text = "\n".join(lines)

        # 5) Send to the main ESC/POS printer
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
        """
        Prints the full Z‑hesabat (detailed) for shift stat_id,
        matching the second receipt layout exactly.
        """
        # 1) Load the Statistics record
        try:
            stat = Statistics.objects.get(pk=stat_id)
        except Statistics.DoesNotExist:
            return False, f"Statistika id={stat_id} tapılmadı."

        # 2) Read pre‑computed totals
        cash = stat.cash_total
        card = stat.card_total
        other = stat.other_total
        total = cash + card + other

        # 3) Count of operations (e.g. number of paid orders)
        op_count = stat.orders.count()

        # 4) Sum of any open (unpaid) orders
        open_sum = Order.objects.filter(is_paid=False)\
                                .aggregate(total=Sum('total_price'))['total'] or 0

        # 5) Build the lines
        width = 48
        lines = []

        # Header
        lines.append("Z‑hesabat")
        main_printer = Printer.objects.filter(is_main=True).first()
        term = main_printer.name if main_printer else "N/A"
        lines.append(f"Terminal:        {term}")
        lines.append(f"Kassa növbəsi:   {stat.id}")
        lines.append(
            f"Status: {'Təsdiqlənib' if stat.is_z_checked else 'Qaralama'}"
        )
        lines.append(
            f"Növbə açıldı:    {stat.start_time.strftime('%d.%m.%Y %H:%M')}")
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        lines.append(f"Cari vaxt:       {now}")
        if user:
            name = user.get_full_name() or user.username
            lines.append(f"Cari istifadəçi: {name}")
        lines.append("")

        # Nağd section
        lines.append("Nağd")
        lines.append(f"Satış       {cash:>10.2f}")
        lines.append(f"Qaytarılma  {0:>10.2f}")
        lines.append(f"Alış        {0:>10.2f}")
        lines.append(f"Alışın qaytar.{0:>10.2f}")
        lines.append("")

        # Bank kartları
        lines.append("Bank kartları")
        lines.append(f"Satış       {card:>10.2f}")
        lines.append(f"Qaytarılma  {0:>10.2f}")
        lines.append("")

        # Cəmi
        lines.append(f"Cəmi        {total:>10.2f}")
        lines.append(f"Satış       {0:>10.2f}")
        lines.append(f"Qaytarılma  {0:>10.2f}")
        lines.append(f"Alış        {0:>10.2f}")
        lines.append(f"Alışın qaytar.{0:>10.2f}")
        lines.append(f"Möhkmlətmə  {0:>10.2f}")
        lines.append(f"İnkassasiya {0:>10.2f}")
        lines.append("")

        # Open orders
        lines.append(f"Açıq sifarişlər        {open_sum:.2f}")
        lines.append("")

        # Operations count
        lines.append(f"YERİNƏ YETİRİLƏN ƏMƏLİYYATLAR {op_count}")
        lines.append(f"Satış       {0}")
        lines.append(f"Qaytarılma  {0}")
        lines.append(f"Alış        {0}")
        lines.append(f"Alışın qaytar.{0}")
        lines.append(f"Möhkmlətmə  {0}")
        lines.append(f"İnkassasiya {0}")
        lines.append("")

        # Footer
        lines.append("Diqqət! Gösterilen məbləğlər")
        lines.append("fiskal registr…")
        lines.append("")

        text = "\n".join(lines)

        # 6) Send to the main printer
        response = PrinterService._send_text_to_main_printer(
            text,
            payment=None,
            type=Receipt.ReceiptType.Z_SUMMRY
        )

        if response.status_code == 200:
            return True, "Z‑hesabat uğurla çap edildi."
        return False, "Printerə qoşulmaq mümkün olmadı."

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
