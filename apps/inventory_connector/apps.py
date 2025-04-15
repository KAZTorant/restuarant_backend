from django.apps import AppConfig
from django.db.models.signals import pre_save, post_save, post_delete


class InventoryConnectorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory_connector'
    verbose_name = "Anbar Əlaqələri"

    def ready(self):
        from apps.inventory_connector.signals import OrderItemInventoryManager
        from apps.orders.models import OrderItem
        # Connect the signals to the static methods of OrderItemInventoryManager.
        pre_save.connect(
            OrderItemInventoryManager.pre_save, sender=OrderItem
        )
        post_save.connect(
            OrderItemInventoryManager.post_save, sender=OrderItem
        )
        post_delete.connect(
            OrderItemInventoryManager.post_delete, sender=OrderItem
        )
