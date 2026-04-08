from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.printers.models import Receipt
from apps.printers.serializers import (ReceiptDetailSerializer,
                                       ReceiptSerializer)
from apps.users.permissions import IsAdminPanelUser


class ReceiptPagination(PageNumberPagination):
    """
    Receipt-lər üçün pagination.
    
    Query params:
      - page       : səhifə nömrəsi (default: 1)
      - page_size  : səhifə ölçüsü (default: 20, max: 100)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            'pagination': {
                'count': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'results': data
        })


class ReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Çek (Receipt) API - Yalnız oxuma (Read-Only)
    
    Çeklər sistem tərəfindən avtomatik yaradılır, ona görə yalnız oxuma əməliyyatları mövcuddur.
    
    list: Bütün çekləri listələ
    retrieve: Tək çekin detayını gətir
    """
    permission_classes = [IsAuthenticated, IsAdminPanelUser]
    queryset = Receipt.objects.all().prefetch_related('orders', 'payment')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['text']
    ordering_fields = ['id', 'created_at']
    ordering = ['-created_at']
    filterset_fields = ['type', 'printer_response_status_code']
    pagination_class = ReceiptPagination
    
    def get_serializer_class(self):
        """Action-a görə serializer seç"""
        if self.action == 'retrieve':
            return ReceiptDetailSerializer
        return ReceiptSerializer
    
    def list(self, request, *args, **kwargs):
        """Çekləri listələ"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Tarix filtrasiyası əlavə et
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
