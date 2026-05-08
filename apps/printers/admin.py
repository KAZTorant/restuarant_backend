# printers/admin.py

from django import forms
from django.contrib import admin, messages
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import redirect

from apps.printers.models import Printer
from apps.printers.models import PreparationPlace
from apps.printers.models import Receipt
from apps.printers.utils.print_test_page import send_raw_receipt
from apps.printers.utils.printer_discovery import discover_all_printers


class PrinterForm(forms.ModelForm):
    class Meta:
        model = Printer
        fields = '__all__'


class PrinterAdmin(admin.ModelAdmin):
    form = PrinterForm
    actions = ["send_test_page_action"]

    class Media:
        # The JavaScript file path should be relative to your static files directory
        js = ('admin/js/printer_scan.js',)

    def send_test_page_action(self, request, queryset):
        for printer in queryset:
            success, msg = send_raw_receipt(printer.ip_address, printer.port)
            if success:
                self.message_user(request, msg, level=messages.SUCCESS)
            else:
                self.message_user(
                    request, f"Failed to send test page to {printer.name}: {msg}", level=messages.ERROR)

    send_test_page_action.short_description = "Send test page to selected printers"

    def get_urls(self):

        custom_urls = [
            path(
                'scan-printers/',
                self.admin_site.admin_view(self.scan_printers_view),
                name='scan_printers'
            ),
        ]
        return custom_urls + super().get_urls()  # 👈 custom URLs əvvəl gəlməlidir!

    def scan_printers_view(self, request):
        """
        AJAX view that scans for available printers on the local network.
        Returns a JSON list of printers with their IP addresses and (dummy) names.
        """
        # Returns a list of dicts like [{'ip': '192.168.1.10', 'name': 'POS Printer'}, ...]
        printers = discover_all_printers()
        return JsonResponse(printers, safe=False)


admin.site.register(Printer, PrinterAdmin)


@admin.register(PreparationPlace)
class PreparationPlaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'printer']
    search_fields = ['name']
    list_filter = ['printer']


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'created_at', 'type',
        'table_display',
        'printer_response_status_code',
        'reprint_button',
    )
    list_filter = ('type', 'created_at', 'printer_response_status_code')
    search_fields = ('text',)
    readonly_fields = (
        'created_at', 'text', 'orders',
        'payment', 'printer_response_status_code',
        'type',
    )

    fieldsets = (
        (None, {
            'fields': (
                'type',
                'created_at',
                'printer_response_status_code',
                'orders',
                'payment',
                'text',
            )
        }),
    )

    def table_display(self, obj):
        # Try to get table from payment first, then from orders
        if obj.payment and obj.payment.table:
            t = obj.payment.table
            room = t.room.name if t.room else ""
            return f"{room} - Masa {t.number}" if room else f"Masa {t.number}"
        # Use all_orders() to include soft-deleted orders as well
        from apps.orders.models import Order
        order = Order.objects.all_orders().filter(receipts=obj).first()
        if order and order.table:
            t = order.table
            room = t.room.name if t.room else ""
            return f"{room} - Masa {t.number}" if room else f"Masa {t.number}"
        return "-"
    table_display.short_description = "Masa"

    def reprint_button(self, obj):
        url = f"reprint/{obj.pk}/"
        return format_html(
            '<a class="button" href="{}" style="'
            'background:#417690;color:#fff;padding:4px 10px;'
            'border-radius:4px;text-decoration:none;font-size:12px;">'
            '🖨 Çap et</a>',
            url
        )
    reprint_button.short_description = "Çap"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'reprint/<int:receipt_id>/',
                self.admin_site.admin_view(self.reprint_receipt_view),
                name='receipt_reprint',
            ),
        ]
        return custom + urls

    def reprint_receipt_view(self, request, receipt_id):
        from apps.printers.utils.service_v2 import PrinterService

        try:
            receipt = Receipt.objects.get(pk=receipt_id)
        except Receipt.DoesNotExist:
            self.message_user(request, "Çek tapılmadı.", level=messages.ERROR)
            return redirect('../../')

        if not receipt.text:
            self.message_user(request, "Çekin mətni boşdur.", level=messages.ERROR)
            return redirect('../../')

        # Determine target printer: worker or main
        if receipt.type == Receipt.ReceiptType.PREPERATION_PLACE:
            # Find worker printer from the order items' preparation places
            order = receipt.orders.first()
            worker_printer = None
            if order:
                for item in order.order_items.all():
                    prep_places = item.meal.get_all_preparation_places()
                    if prep_places and prep_places[0].printer:
                        worker_printer = prep_places[0].printer
                        break

            if not worker_printer:
                # Fallback: use first non-main printer
                worker_printer = Printer.objects.filter(is_main=False).first()

            if not worker_printer:
                self.message_user(request, "Worker printer tapılmadı.", level=messages.ERROR)
                return redirect('../../')

            response = PrinterService._send_text_to_printer(
                receipt.text,
                worker_printer.ip_address,
                worker_printer.port,
            )
        else:
            response = PrinterService._send_text_to_main_printer(receipt.text)

        if response.status_code == 200:
            self.message_user(request, f"#{receipt_id} çeki uğurla çap edildi.")
        else:
            self.message_user(request, "Printer qoşulmayıb və ya xəta baş verdi.", level=messages.ERROR)

        return redirect('../../')