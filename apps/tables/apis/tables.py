from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.db.models import Prefetch
from django.utils.decorators import method_decorator

from apps.tenants.cache import tenant_cache_page
from apps.tenants.utils import filter_by_restaurant
from apps.orders.models import Order
from apps.tables.models import Room, Table

from apps.tables.serializers import TableSerializer
from apps.tables.serializers import TableDetailSerializer
from apps.tables.serializers import RoomSerializer


class TableAPIView(ListAPIView):
    model = Table
    serializer_class = TableSerializer

    def get_queryset(self):
        room_id = self.kwargs.get("room_id", None)
        qs = Table.objects.filter(room__id=room_id).order_by("id")
        # This endpoint is polled every few seconds by the floor plan, so load
        # every table's open orders (and their waitress) in one extra query
        # instead of several queries per table. ``Order.objects`` already
        # excludes deleted orders. See ``TableSerializer``.
        open_orders = (
            Order.objects.filter(is_paid=False)
            .select_related("waitress")
            .order_by("pk")
        )
        qs = qs.prefetch_related(
            Prefetch("orders", queryset=open_orders, to_attr="open_orders_cache")
        )
        return filter_by_restaurant(qs)


class RoomAPIView(ListAPIView):
    model = Room
    serializer_class = RoomSerializer

    def get_queryset(self):
        qs = Room.objects.filter(is_active=True)
        return filter_by_restaurant(qs)

    @method_decorator(tenant_cache_page(settings.CACHE_TIME_IN_SECONDS))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class TableDetailAPIView(APIView):

    def get(self, request, table_id):
        qs = filter_by_restaurant(Table.objects.filter(id=table_id))
        table = qs.first()

        if not table:
            return Response(
                {},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = TableDetailSerializer(
            instance=table,
            context={"user": request.user}
        )

        return Response(
            data=serializer.data,
            status=status.HTTP_200_OK
        )
