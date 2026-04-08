from rest_framework import filters, generics, status
from rest_framework.response import Response

from apps.tables.apis.admin.serializers import (AdminRoomDetailSerializer,
                                                AdminRoomSerializer,
                                                AdminTableDetailSerializer,
                                                AdminTableSerializer)
from apps.tables.models import Room, Table
from apps.users.permissions import IsAdminPanelUser


class AdminRequiredMixin:
    """Superuser, staff, admin və ya restaurant owner tələb edir"""
    permission_classes = [IsAdminPanelUser]


# ─────────────────────────────────────────────
#  ROOM (Zal)
# ─────────────────────────────────────────────

class AdminRoomListCreateAPIView(AdminRequiredMixin, generics.ListCreateAPIView):
    """
    GET  → Bütün zalların siyahısı (axtarış + sıralama dəstəklənir)
    POST → Yeni zal yarat
    """
    queryset = Room.objects.all().order_by("id")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["id", "name", "created_at"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdminRoomDetailSerializer
        return AdminRoomSerializer


class AdminRoomRetrieveUpdateDestroyAPIView(AdminRequiredMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → Zal detalları (cədvəl sayı ilə)
    PUT    → Tam yenilə
    PATCH  → Qismən yenilə
    DELETE → Sil
    """
    queryset = Room.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdminRoomDetailSerializer
        return AdminRoomSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        tables_count = instance.tables.count()
        if tables_count > 0:
            return Response(
                {
                    "error": f"Bu zalda {tables_count} stol var. "
                             "Əvvəlcə stolları silin və ya başqa zala köçürün."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
#  TABLE (Stol)
# ─────────────────────────────────────────────

class AdminTableListCreateAPIView(AdminRequiredMixin, generics.ListCreateAPIView):
    """
    GET  → Bütün stolların siyahısı (zala görə filter + axtarış)
    POST → Yeni stol yarat
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["number", "room__name"]
    ordering_fields = ["id", "number", "capacity", "created_at"]

    def get_queryset(self):
        qs = Table.objects.select_related("room").order_by("id")
        room_id = self.request.query_params.get("room_id")
        if room_id:
            qs = qs.filter(room__id=room_id)
        return qs

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdminTableDetailSerializer
        return AdminTableSerializer


class AdminTableRetrieveUpdateDestroyAPIView(AdminRequiredMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → Stol detalları
    PUT    → Tam yenilə
    PATCH  → Qismən yenilə
    DELETE → Sil
    """
    queryset = Table.objects.select_related("room")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdminTableDetailSerializer
        return AdminTableSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.assignable_table:
            return Response(
                {
                    "error": "Bu stolun aktiv sifarişi var. "
                             "Əvvəlcə sifarişi bağlayın."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
