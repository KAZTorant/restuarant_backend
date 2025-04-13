from django.db.models.signals import post_save
from django.dispatch import receiver

from inventory.models import InventoryRecord
from apps.orders.models import OrderItem


@receiver(post_save, sender=OrderItem)
def update_inventory_on_order_item_confirmation(sender, instance, created, **kwargs):
    """
    When an OrderItem is confirmed, update inventory by creating a removal record
    for each inventory item linked to the meal via the MealInventoryConnector.
    """
    try:
        # Process only if this OrderItem is confirmed
        if instance.confirmed:
            # Get the MealInventoryConnector from the Meal instance (via the related_name 'inventory_connector')
            connector = getattr(instance.meal, 'inventory_connector', None)
            if not connector:
                return  # No connector found for this meal

            # Retrieve all mapping records from the connector
            mappings = connector.mappings.all()
            for mapping in mappings:
                # Calculate the amount to remove: (mapping.quantity per meal) * (order item quantity)
                remove_quantity = mapping.quantity * instance.quantity

                # Create a new inventory record to remove stock
                InventoryRecord.objects.create(
                    inventory_item=mapping.inventory_item,
                    quantity=remove_quantity,
                    record_type='remove',
                    reason='sold',
                    # Adjust as needed for your pricing logic
                    price=round(instance.meal.price * remove_quantity, 3)
                )
    except Exception as error:
        print(error)
