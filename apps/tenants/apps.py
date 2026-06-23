from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenants'
    verbose_name = 'Restoranlar'

    def ready(self):
        from apps.tenants.inventory_patch import patch_inventory_admin, patch_inventory_models

        patch_inventory_models()
        patch_inventory_admin()
