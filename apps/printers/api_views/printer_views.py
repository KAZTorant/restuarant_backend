from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.printers.models import Printer
from apps.printers.serializers import (PrinterCreateSerializer,
                                       PrinterSerializer,
                                       PrinterUpdateSerializer)
from apps.users.permissions import IsAdminPanelUser


class PrinterViewSet(viewsets.ModelViewSet):
    """
    Printer CRUD API
    
    list: Bütün printerləri listələ
    retrieve: Tək printerin detayını gətir
    create: Yeni printer yarat
    update: Printeri tam yenilə (PUT)
    partial_update: Printeri qismən yenilə (PATCH)
    destroy: Printeri sil
    """
    permission_classes = [IsAuthenticated, IsAdminPanelUser]
    queryset = Printer.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'ip_address', 'description']
    ordering_fields = ['id', 'name', 'created_at']
    ordering = ['-id']
    filterset_fields = ['is_main']
    
    def get_serializer_class(self):
        """Action-a görə serializer seç"""
        if self.action == 'create':
            return PrinterCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PrinterUpdateSerializer
        return PrinterSerializer
    
    def create(self, request, *args, **kwargs):
        """Yeni printer yarat"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        printer = serializer.save()
        
        # Response üçün detail serializer istifadə et
        response_serializer = PrinterSerializer(printer)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Printeri yenilə"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        printer = serializer.save()
        
        # Response üçün detail serializer istifadə et
        response_serializer = PrinterSerializer(printer)
        return Response(response_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Printeri sil"""
        instance = self.get_object()
        
        # Əgər bu printer hazırlanma yerlərində istifadə olunursa, silməyə icazə vermə
        if instance.preparationplace_set.exists():
            return Response(
                {
                    "error": "Bu printer hazırlanma yerlərində istifadə olunur. Əvvəlcə hazırlanma yerlərindən silin."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.delete()
        return Response(
            {"message": "Printer uğurla silindi."},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['post'], url_path='set-main')
    def set_main(self, request, pk=None):
        """Bu printeri əsas printer et"""
        printer = self.get_object()
        
        # Bütün printerlərin is_main-ini False et
        Printer.objects.all().update(is_main=False)
        
        # Bu printeri main et
        printer.is_main = True
        printer.save()
        
        serializer = self.get_serializer(printer)
        return Response({
            "message": f"{printer.name} əsas printer olaraq təyin edildi.",
            "data": serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='main-printer')
    def main_printer(self, request):
        """Əsas printeri gətir"""
        printer = Printer.objects.filter(is_main=True).first()
        
        if not printer:
            return Response(
                {"error": "Əsas printer tapılmadı."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(printer)
        return Response(serializer.data)
