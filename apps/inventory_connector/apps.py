from django.apps import AppConfig


class InventoryConnectorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory_connector'
    verbose_name = "Anbar Əlaqələri"

    def ready(self):
        from apps.inventory_connector.signals import update_inventory_on_order_item_confirmation
