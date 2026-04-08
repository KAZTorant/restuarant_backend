from apps.printers.api_views.place_views import PreparationPlaceViewSet
from apps.printers.api_views.printer_actions import ScanPrintersAPIView, TestPrintAPIView
from apps.printers.api_views.printer_views import PrinterViewSet
from apps.printers.api_views.receipt_views import ReceiptViewSet

__all__ = [
    'PrinterViewSet',
    'PreparationPlaceViewSet',
    'ReceiptViewSet',
    'ScanPrintersAPIView',
    'TestPrintAPIView',
]
