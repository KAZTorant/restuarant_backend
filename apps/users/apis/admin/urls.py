from django.urls import path

from apps.users.apis.admin.views import (
    AdminGroupListCreateAPIView, AdminGroupRetrieveUpdateDestroyAPIView,
    AdminPermissionListAPIView, AdminUserListCreateAPIView,
    AdminUserRetrieveUpdateDestroyAPIView, AdminUserSetPasswordAPIView)

urlpatterns = [
    # ── Permissions (read-only, group assign üçün) ─────────────
    path(
        "permissions/",
        AdminPermissionListAPIView.as_view(),
        name="admin-permission-list",
    ),

    # ── Groups (Qruplar) ───────────────────────────────────────
    path(
        "groups/",
        AdminGroupListCreateAPIView.as_view(),
        name="admin-group-list-create",
    ),
    path(
        "groups/<int:pk>/",
        AdminGroupRetrieveUpdateDestroyAPIView.as_view(),
        name="admin-group-detail",
    ),

    # ── Users (İstifadəçilər) ──────────────────────────────────
    path(
        "users/",
        AdminUserListCreateAPIView.as_view(),
        name="admin-user-list-create",
    ),
    path(
        "users/<int:pk>/",
        AdminUserRetrieveUpdateDestroyAPIView.as_view(),
        name="admin-user-detail",
    ),
    path(
        "users/<int:pk>/set-password/",
        AdminUserSetPasswordAPIView.as_view(),
        name="admin-user-set-password",
    ),
]
