from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from apps.tenants.utils import filter_by_restaurant
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
        return filter_by_restaurant(qs)


class RoomAPIView(ListAPIView):
    model = Room
    serializer_class = RoomSerializer

    def get_queryset(self):
        qs = Room.objects.filter(is_active=True)
        return filter_by_restaurant(qs)

    @method_decorator(cache_page(settings.CACHE_TIME_IN_SECONDS))
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
