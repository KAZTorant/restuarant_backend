from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from apps.users.permissions import AtMostAdmin


class CreateOrderAPIView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, AtMostAdmin]

    def create(self, request, *args, **kwargs):
        # Get table id from the URL kwargs:
        table_id = self.kwargs.get("table_id")
        # Get customer_count from the request data, defaulting to 1 if not provided.
        customer_count = (request.data or {}).get("customer_count", 1)
        data = {
            'table': table_id,
            'customer_count': customer_count,
        }

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            order = serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
