from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.printers.api_views import (PreparationPlaceViewSet, PrinterViewSet,
                                     ReceiptViewSet, ScanPrintersAPIView,
                                     TestPrintAPIView)
from apps.printers.apis import PrintCheckAPIView

# Router yaradırıq
router = DefaultRouter()
router.register(r'printers', PrinterViewSet, basename='printer')
router.register(r'preparation-places', PreparationPlaceViewSet, basename='preparation-place')
router.register(r'receipts', ReceiptViewSet, basename='receipt')

urlpatterns = [
    # Printer action endpoints (router-dən əvvəl olmalıdır)
    path('printers/scan/', ScanPrintersAPIView.as_view(), name='printer-scan'),
    path('printers/test-print/', TestPrintAPIView.as_view(), name='printer-test-print'),
    
    # Router URLs
    path('', include(router.urls)),
    
    # Köhnə print check endpoint (əvvəlki funksionallığı saxla)
    path(
        '<int:table_id>/print-check/',
        PrintCheckAPIView.as_view(),
        name='print-check'
    ),
]
