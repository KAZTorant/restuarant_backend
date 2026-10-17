from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'
    verbose_name = "Sifariş"

    def ready(self):
        from django.contrib import admin
        from django.urls import path

        from apps.orders.admin.analytics import analytics_data, analytics_page

        if getattr(admin.site, '_sales_analytics_patched', False):
            return

        original_get_urls = admin.site.get_urls

        def get_urls():
            custom = [
                path(
                    'analytics/',
                    admin.site.admin_view(analytics_page),
                    name='sales_analytics',
                ),
                path(
                    'analytics/data/',
                    admin.site.admin_view(analytics_data),
                    name='sales_analytics_data',
                ),
            ]
            return custom + original_get_urls()

        admin.site.get_urls = get_urls
        admin.site._sales_analytics_patched = True
