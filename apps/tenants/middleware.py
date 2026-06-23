from django.http import Http404

from apps.tenants.context import clear_current_restaurant, set_current_restaurant
from apps.tenants.models import Restaurant


class TenantMiddleware:
    """Resolve current restaurant from session, header, or URL path."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        restaurant = self._resolve_restaurant(request)
        if restaurant is not None:
            set_current_restaurant(restaurant)
            request.restaurant = restaurant
        else:
            request.restaurant = None

        try:
            response = self.get_response(request)
        finally:
            clear_current_restaurant()

        return response

    def _resolve_restaurant(self, request):
        slug = self._slug_from_path(request.path)
        if slug:
            return self._get_active_restaurant(slug)

        slug = request.headers.get('X-Restaurant-Slug')
        if slug:
            return self._get_active_restaurant(slug)

        restaurant_id = request.session.get('restaurant_id')
        if restaurant_id:
            return Restaurant.objects.filter(pk=restaurant_id, is_active=True).first()

        user = getattr(request, 'user', None)
        if user and user.is_authenticated and hasattr(user, 'restaurant_id'):
            if user.restaurant_id and user.is_active:
                return user.restaurant

        return None

    def _slug_from_path(self, path):
        parts = path.strip('/').split('/')
        if len(parts) >= 2 and parts[0] == 'r':
            return parts[1]
        return None

    def _get_active_restaurant(self, slug):
        try:
            return Restaurant.objects.get(slug=slug, is_active=True)
        except Restaurant.DoesNotExist:
            raise Http404('Restoran tapılmadı.')
