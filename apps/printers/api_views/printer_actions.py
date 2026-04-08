from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.printers.utils.printer_discovery import discover_all_printers
from apps.printers.utils.print_test_page import send_raw_receipt
from apps.printers.models import Printer
from apps.users.permissions import IsAdminPanelUser


class ScanPrintersAPIView(APIView):
    """
    Şəbəkədəki printerləri scan et
    
    GET: Şəbəkədə mövcud olan printerləri tap və qaytır
    """
    permission_classes = [IsAuthenticated, IsAdminPanelUser]
    
    def get(self, request):
        """Şəbəkədəki printerləri scan et"""
        try:
            # Printer discovery funksiyası ilə printerləri tap
            printers = discover_all_printers()
            
            return Response({
                "success": True,
                "message": f"{len(printers)} printer tapıldı.",
                "printers": printers
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Printer scan zamanı xəta baş verdi: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestPrintAPIView(APIView):
    """
    Printerə test print göndər
    
    POST: Müəyyən printerə test səhifəsi göndər
    Body: {
        "printer_id": 1  // və ya
        "ip_address": "192.168.1.100",
        "port": 9100
    }
    """
    permission_classes = [IsAuthenticated, IsAdminPanelUser]
    
    def post(self, request):
        """Printerə test print göndər"""
        printer_id = request.data.get('printer_id')
        ip_address = request.data.get('ip_address')
        port = request.data.get('port', 9100)
        
        # Əgər printer_id verilsə, DB-dən götür
        if printer_id:
            try:
                printer = Printer.objects.get(id=printer_id)
                ip_address = printer.ip_address
                port = printer.port
            except Printer.DoesNotExist:
                return Response({
                    "success": False,
                    "error": "Printer tapılmadı."
                }, status=status.HTTP_404_NOT_FOUND)
        
        # IP address mütləq olmalıdır
        if not ip_address:
            return Response({
                "success": False,
                "error": "IP address və ya printer_id göndərilməlidir."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Test print göndər
        try:
            success, message = send_raw_receipt(ip_address, port)
            
            if success:
                return Response({
                    "success": True,
                    "message": message
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "error": message
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                "success": False,
                "error": f"Test print zamanı xəta: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
