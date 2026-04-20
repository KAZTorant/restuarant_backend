from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import filters, status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.orders.models import Statistics
from apps.orders.serializers.statistics import StatisticsSummarySerializer


class StatisticsListAPIView(ListAPIView):
    """
    API endpoint to list all statistics/shifts (hesabatlar).
    
    Query parameters:
    - start_date: Filter by date (YYYY-MM-DD)
    - end_date: Filter by date (YYYY-MM-DD)
    - is_closed: Filter by closed status (true/false)
    - started_by: Filter by username who started the shift
    - ordering: Sort by field (e.g., -start_time, end_time)
    
    Returns:
    - List of statistics with summary information
    """
    serializer_class = StatisticsSummarySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['start_time', 'end_time', 'total', 'date']
    ordering = ['-start_time']  # Default: newest first

    def get_queryset(self):
        queryset = Statistics.objects.filter(
            title='till_now'
        ).select_related('started_by', 'ended_by').prefetch_related('orders')
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            parsed_start_date = parse_date(start_date)
            if parsed_start_date:
                queryset = queryset.filter(start_time__date__gte=parsed_start_date)
        
        if end_date:
            parsed_end_date = parse_date(end_date)
            if parsed_end_date:
                queryset = queryset.filter(
                    Q(end_time__date__lte=parsed_end_date) | Q(end_time__isnull=True)
                )
        
        # Filter by closed status
        is_closed = self.request.query_params.get('is_closed')
        if is_closed is not None:
            if is_closed.lower() == 'true':
                queryset = queryset.filter(is_closed=True)
            elif is_closed.lower() == 'false':
                queryset = queryset.filter(is_closed=False)
        
        # Filter by user who started
        started_by = self.request.query_params.get('started_by')
        if started_by:
            queryset = queryset.filter(started_by__username=started_by)
        
        return queryset
