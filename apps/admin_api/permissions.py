from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Only staff users can access the admin API."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
