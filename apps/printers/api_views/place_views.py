from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.printers.models import PreparationPlace
from apps.printers.serializers import (PreparationPlaceCreateSerializer,
                                       PreparationPlaceSerializer,
                                       PreparationPlaceUpdateSerializer)
from apps.users.permissions import IsAdminPanelUser


class PreparationPlaceViewSet(viewsets.ModelViewSet):
    """
    Hazırlanma Yeri CRUD API
    
    list: Bütün hazırlanma yerlərini listələ
    retrieve: Tək hazırlanma yerinin detayını gətir
    create: Yeni hazırlanma yeri yarat
    update: Hazırlanma yerini tam yenilə (PUT)
    partial_update: Hazırlanma yerini qismən yenilə (PATCH)
    destroy: Hazırlanma yerini sil
    """
    permission_classes = [IsAuthenticated, IsAdminPanelUser]
    queryset = PreparationPlace.objects.all().select_related('printer')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['id', 'name']
    ordering = ['name']
    filterset_fields = ['printer']
    
    def get_serializer_class(self):
        """Action-a görə serializer seç"""
        if self.action == 'create':
            return PreparationPlaceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PreparationPlaceUpdateSerializer
        return PreparationPlaceSerializer
    
    def create(self, request, *args, **kwargs):
        """Yeni hazırlanma yeri yarat"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        place = serializer.save()
        
        # Response üçün detail serializer istifadə et
        response_serializer = PreparationPlaceSerializer(place)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Hazırlanma yerini yenilə"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        place = serializer.save()
        
        # Response üçün detail serializer istifadə et
        response_serializer = PreparationPlaceSerializer(place)
        return Response(response_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Hazırlanma yerini sil"""
        instance = self.get_object()
        instance.delete()
        
        return Response(
            {"message": "Hazırlanma yeri uğurla silindi."},
            status=status.HTTP_204_NO_CONTENT
        )
