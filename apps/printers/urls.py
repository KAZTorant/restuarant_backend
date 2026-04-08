from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.printers.apis import PrintCheckAPIView
from apps.printers.api_views import (
    PrinterViewSet,
    PreparationPlaceViewSet,
    ReceiptViewSet,
    ScanPrintersAPIView,
    TestPrintAPIView
)

# Router yaradırıq
router = DefaultRouter()
router.register(r'printers', PrinterViewSet, basename='printer')
router.register(r'preparation-places', PreparationPlaceViewSet, basename='preparation-place')
router.register(r'receipts', ReceiptViewSet, basename='receipt')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Printer action endpoints
    path('printers/scan/', ScanPrintersAPIView.as_view(), name='printer-scan'),
    path('printers/test-print/', TestPrintAPIView.as_view(), name='printer-test-print'),
    
    # Köhnə print check endpoint (əvvəlki funksionallığı saxla)
    path(
        '<int:table_id>/print-check/',
        PrintCheckAPIView.as_view(),
        name='print-check'
    ),
]
