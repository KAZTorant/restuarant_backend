from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django.utils.dateparse import parse_date
from apps.orders.models import Statistics
from apps.orders.serializers.statistics import WithdrawnInfoSerializer, StatisticsSummarySerializer


class WithdrawnInfoListAPIView(generics.ListAPIView):
    """
    API endpoint to list all withdrawn amounts and notes from closed shifts.
    
    Query parameters:
    - start_date: Filter shifts closed on or after this date (YYYY-MM-DD)
    - end_date: Filter shifts closed on or before this date (YYYY-MM-DD)
    - has_withdrawn: Filter shifts that have withdrawn amounts (true/false)
    """
    serializer_class = WithdrawnInfoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['end_time', 'start_time', 'withdrawn_amount']
    ordering = ['-end_time']  # Default ordering by end_time descending
    
    def get_queryset(self):
        queryset = Statistics.objects.filter(
            title='till_now',
            is_closed=True
        ).select_related('started_by', 'ended_by')
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            parsed_start_date = parse_date(start_date)
            if parsed_start_date:
                queryset = queryset.filter(end_time__date__gte=parsed_start_date)
        
        if end_date:
            parsed_end_date = parse_date(end_date)
            if parsed_end_date:
                queryset = queryset.filter(end_time__date__lte=parsed_end_date)
        
        # Filter by withdrawn amount
        has_withdrawn = self.request.query_params.get('has_withdrawn')
        if has_withdrawn and has_withdrawn.lower() == 'true':
            queryset = queryset.exclude(withdrawn_amount=0)
        
        return queryset


class WithdrawnInfoDetailAPIView(generics.RetrieveAPIView):
    """
    API endpoint to get detailed information about a specific shift's withdrawn info.
    """
    serializer_class = WithdrawnInfoSerializer
    permission_classes = [IsAuthenticated]
    queryset = Statistics.objects.filter(
        title='till_now',
        is_closed=True
    ).select_related('started_by', 'ended_by')
