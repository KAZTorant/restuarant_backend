from django.urls import path

from apps.tables.apis.admin.views import (
    AdminRoomListCreateAPIView, AdminRoomRetrieveUpdateDestroyAPIView,
    AdminTableListCreateAPIView, AdminTableRetrieveUpdateDestroyAPIView)

urlpatterns = [
    # ── Rooms (Zallar) ────────────────────────────────────────
    path(
        "rooms/",
        AdminRoomListCreateAPIView.as_view(),
        name="admin-room-list-create",
    ),
    path(
        "rooms/<int:pk>/",
        AdminRoomRetrieveUpdateDestroyAPIView.as_view(),
        name="admin-room-detail",
    ),

    # ── Tables (Stollar) ──────────────────────────────────────
    path(
        "tables/",
        AdminTableListCreateAPIView.as_view(),
        name="admin-table-list-create",
    ),
    path(
        "tables/<int:pk>/",
        AdminTableRetrieveUpdateDestroyAPIView.as_view(),
        name="admin-table-detail",
    ),
]
