from django.db.models import Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order


class ActiveOrdersStatsAPIView(APIView):
    """
    API endpoint to get statistics about active orders (paid and unpaid).
    
    This is useful for real-time monitoring of restaurant operations.
    
    Returns:
    - total_paid: Sum of all paid orders
    - total_unpaid: Sum of all unpaid orders
    - paid_count: Number of paid orders
    - unpaid_count: Number of unpaid orders
    - grand_total: Sum of paid + unpaid
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get paid orders
        paid_data = Order.objects.filter(is_paid=True).aggregate(
            sum=Sum('total_price'),
            count=Sum('id')
        )
        paid_sum = paid_data['sum'] or 0
        paid_count = Order.objects.filter(is_paid=True).count()

        # Get unpaid orders
        unpaid_data = Order.objects.filter(is_paid=False).aggregate(
            sum=Sum('total_price'),
            count=Sum('id')
        )
        unpaid_sum = unpaid_data['sum'] or 0
        unpaid_count = Order.objects.filter(is_paid=False).count()

        return Response({
            'total_paid': str(paid_sum),
            'total_unpaid': str(unpaid_sum),
            'paid_count': paid_count,
            'unpaid_count': unpaid_count,
            'grand_total': str(paid_sum + unpaid_sum),
        }, status=status.HTTP_200_OK)
