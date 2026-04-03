from rest_framework import permissions


class IsWaitress(permissions.BasePermission):
    message = 'You must be a waitress to access this endpoint.'

    def has_permission(self, request, view):
        return request.user.type == 'waitress'


class IsAdmin(permissions.BasePermission):
    message = 'You must be an admin to access this endpoint.'

    def has_permission(self, request, view):
        return request.user.type == 'admin'


class IsRestaurantOwner(permissions.BasePermission):
    message = 'You must be a restaurant owner to access this endpoint.'

    def has_permission(self, request, view):
        return request.user.type == 'restaurant'


class IsAdminPanelUser(permissions.BasePermission):
    """
    Admin panelə girişi olan bütün istifadəçilər:
      - is_superuser = True  (Django superadmin)
      - is_staff = True      (Django staff)
      - type = 'admin'       (App admin)
      - type = 'restaurant'  (Restaurant sahibi)
    """
    message = 'Bu endpointe girişiniz yoxdur. Admin, Restaurant, Superuser və ya Staff olmalısınız.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        return getattr(user, 'type', None) in ('admin', 'restaurant')


# Define the role hierarchy.
# Lower numbers mean lower privilege.
ROLE_HIERARCHY = {
    'waitress': 1,
    'captain_waitress': 2,
    'admin': 3,
    'restaurant': 4,  # Restaurant owner (highest)
}


class MaximumRolePermission(permissions.BasePermission):
    """
    Grants access only if the user's role level is less than or equal to the specified maximum.
    Subclasses must set the `max_role_level` class attribute.
    """
    max_role_level = None
    message = 'Your role exceeds the maximum level required to access this endpoint.'

    def has_permission(self, request, view):
        user_role = getattr(request.user, 'type', None)
        if not user_role or user_role not in ROLE_HIERARCHY:
            return False
        if self.max_role_level is None:
            return False
        return ROLE_HIERARCHY[user_role] <= self.max_role_level


# --- Specific "At Most" Permission Classes ---

class AtMostWaitress(MaximumRolePermission):
    """
    Allows only waitresses.
    """
    max_role_level = ROLE_HIERARCHY['waitress']
    message = 'Only waitresses are allowed to access this endpoint.'


class AtMostCaptain(MaximumRolePermission):
    """
    Allows waitresses and captain waitresses.
    """
    max_role_level = ROLE_HIERARCHY['captain_waitress']
    message = 'Only waitresses and captain waitresses are allowed to access this endpoint.'


class AtMostAdmin(MaximumRolePermission):
    """
    Allows waitresses, captain waitresses, and admins.
    Restaurant owners are not allowed.
    """
    max_role_level = ROLE_HIERARCHY['admin']
    message = 'Only waitresses, captain waitresses, or admins are allowed to access this endpoint.'
