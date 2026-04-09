from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version='v1',
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.urls')),
    path('orders/', include('apps.orders.apis.urls')),

    # ── Admin Panel APIs ─────────────────────────────────────
    path('api/admin/auth/', include('apps.users.apis.admin_auth_urls')),
    path('api/admin/meals/', include('apps.meals.apis.admin.urls')),
    path('api/admin/tables/', include('apps.tables.apis.admin.urls')),
    path('api/admin/payments/', include('apps.payments.apis.admin.urls')),
    path('api/admin/users/', include('apps.users.apis.admin.urls')),

    # SWAGGER
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api-docs/', schema_view.with_ui('swagger', cache_timeout=0), name='api-docs'),
]
