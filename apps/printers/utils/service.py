import socket
import json
from datetime import datetime
from apps.tables.models import Table
from apps.printers.models import Printer


class DummyResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class PrinterService:
    @staticmethod
    def _generate_order_data(order):
        """Hər sifariş üçün JSON strukturu yaradır."""
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

    @staticmethod
    def generate_receipt_data_for_orders(table, orders):
        """
        Çap üçün printerə göndəriləcək receipt məlumatlarını (JSON) yaradır.
        """
        if not orders:
            return {}

        receipt_data = {
            'date': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'table': {
                'room': table.room.name if table and table.room else 'N/A',
                'number': table.number if table else 'N/A'
            },
            'waitress': table.orders.exclude(is_deleted=True).filter(is_paid=False, is_main=True).first().waitress.get_full_name(),
            'orders': []
        }

        for order in orders:
            receipt_data['orders'].append(
                PrinterService._generate_order_data(order)
            )

        return receipt_data

    def print_orders_for_table(self, table_id, force_print=False):
        """
        Masa nömrəsinə əsasən, çapın icazə verilib-verilmədiyini yoxlayır,
        receipt JSON məlumatlarını yaradır və bunu birbaşa printerə göndərir.
        """
        try:
            table = Table.objects.get(pk=table_id)
            if not table.can_print_check() and not force_print:
                return False, "Aktiv sifariş yoxdur və ya çek artıq çap edilib."

            orders = table.orders.exclude(
                is_deleted=True).filter(is_paid=False)
            receipt_data = self.generate_receipt_data_for_orders(table, orders)
            response = self.send_to_printer(receipt_data)

            if response.status_code == 200:
                orders.update(is_check_printed=True)
                return True, "Çek uğurla çap edildi."
            else:
                return False, "Çek çap edilə bilmədi. Printer qoşulmayıb."
        except Table.DoesNotExist:
            return False, "Masa mövcud deyil."

    def send_to_printer(self, data):
        """
        Şəkillənmiş məlumatı alır, Azərbaycan dilində stilizə edilmiş mətn formatına çevirir 
        və printerə socket vasitəsilə göndərir.
        """
        printer = Printer.objects.filter(is_main=True).first()
        if not printer:
            raise Exception("Sistemdə əsas printer təyin edilməyib.")

        ip_address = printer.ip_address
        port = printer.port

        try:
            # Ümumi receipt genişliyini təyin edirik
            receipt_width = 48
            lines = []

            # Başlıq (mərkəzləşdirilmiş)
            header = "CAFEPARK TAVERN"
            centered_header = header.center(receipt_width)
            lines.append("=" * receipt_width)
            lines.append(centered_header)
            lines.append("=" * receipt_width)

            # Tarix, masa və garson məlumatları
            lines.append(f"Tarix: {data['date']}")
            lines.append(
                f"Masa: {data['table']['room']} - {data['table']['number']}")
            lines.append(f"Garson: {data['waitress']}")
            lines.append("-" * receipt_width)

            # Sifarişlərin siyahısı
            for order in data['orders']:
                # '№' simvolu problem yarada bilər – '#' ilə əvəz olunur.
                lines.append(f"Sifariş #{order['order_id']}")
                for item in order['items']:
                    name = item['name']
                    qty = item['quantity']
                    line_total = item['line_total']
                    # Miqdar, məhsul adı (sola hizalı, genişlik 16) və xətt cəmi (sağa hizalı, genişlik 8)
                    lines.append(f"{qty}x {name:<16}{line_total:>8.2f} AZN")
                lines.append("-" * receipt_width)
                lines.append(f"Cəmi: {order['order_total']:>17.2f} AZN")
                lines.append("-" * receipt_width)

            # Altbilgi
            lines.append("Bizə gəldiyiniz üçün təşəkkürlər!")
            lines.append("=" * receipt_width)
            lines.append("\n\n\n")

            # Bütün sətirləri yekun receipt mətninə birləşdiririk.
            receipt_text = "\n".join(lines)

            # ESC/POS kəsmə əmri (printer dəstəkləyirsə, kağızı kəsmək üçün)
            ESC_CUT = b'\x1D\x56\x00'
            BEEP = b'\x1B\x42\x03\x02'  # Beep 3 times, 200ms each

            # Printerə göndəririk; cp857 kodlaşdırması istifadə olunur.
            with socket.create_connection((ip_address, port), timeout=5) as s:
                s.sendall(
                    receipt_text.encode(
                        'cp857', errors='replace') + ESC_CUT + BEEP
                )

            return DummyResponse(200)
        except Exception as e:
            print(f"Printerə data göndərilərkən xəta: {e}")
            return DummyResponse(500)

    def send_to_worker_printer(self, data, worker_printer):
        """
        Alınan JSON məlumatını alır, işçi üçün nəzərdə tutulmuş stilizə edilmiş mətn formatına çevirir 
        və göstərilən işçi printerinə socket vasitəsilə göndərir.

        data: Receipt JSON məlumatı.
        worker_printer: İşçi printerini təmsil edən Printer instance.
        """
        ip_address = worker_printer.ip_address
        port = worker_printer.port

        try:
            # Ümumi receipt genişliyini təyin edirik.
            receipt_width = 48
            lines = []

            # Başlıq (mərkəzləşdirilmiş) - İşçi üçün Çek
            header = "HAZIRLANMA ÇEKİ"
            centered_header = header.center(receipt_width)
            lines.append("=" * receipt_width)
            lines.append(centered_header)
            lines.append("=" * receipt_width)

            # Tarix və masa məlumatları
            lines.append(f"Tarix: {data['date']}")
            lines.append(
                f"Masa: {data['table']['room']} - {data['table']['number']}")

            # Sifariş nömrəsi (əgər varsa)
            if data['orders']:
                lines.append(f"Sifariş №: {data['orders'][0]['order_id']}")
            else:
                lines.append("Sifariş №: N/A")
            lines.append("-" * receipt_width)

            # Sifarişlərin siyahısı (yalnız ad və miqdar göstərilir)
            for order in data['orders']:
                lines.append(f"Sifariş #{order['order_id']}")
                for item in order['items']:
                    name = item['name']
                    qty = item['quantity']
                    # İşçi üçün yalnız məhsul adı və miqdar kifayət edir.
                    lines.append(f"{qty}x {name}")
                lines.append("-" * receipt_width)

            # Altbilgi: İşçi üçün xüsusi mesaj
            lines.append("Zəhmət olmasa sifarişi düzgün hazırlayın!")
            lines.append("=" * receipt_width)
            lines.append("\n\n\n")

            # Yekun receipt mətnini hazırlayırıq.
            worker_receipt_text = "\n".join(lines)

            # ESC/POS kəsmə əmri (əgər printer dəstəkləyirsə)
            ESC_CUT = b'\x1D\x56\x00'
            BEEP = b'\x1B\x42\x03\x02'  # Beep 3 times, 200ms each

            # Printerə socket vasitəsilə göndəririk; cp857 kodlaşdırması istifadə olunur.
            with socket.create_connection((ip_address, port), timeout=5) as s:
                s.sendall(worker_receipt_text.encode(
                    'cp857', errors='replace') + ESC_CUT + BEEP)

            return DummyResponse(200)
        except Exception as e:
            print(f"İşçi printerinə data göndərilərkən xəta: {e}")
            return DummyResponse(500)
