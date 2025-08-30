
from inventory.models import InventoryRecord
from apps.orders.models import OrderItem


class OrderItemInventoryManager:
    @staticmethod
    def _process_mappings(instance, operation):
        """
        Helper method to create InventoryRecord entries based on OrderItem's mappings.

        operation: 'remove' for deducting inventory,
                   'add' for reversing a deduction (adding stock back).

        For 'remove', the reason will be set as 'sold'.
        For 'add', the reason is now set to 'return' so that the returned product
        from an OrderItem is properly recorded.
        """
        try:
            connector = getattr(instance.meal, 'inventory_connector', None)
            if not connector:
                return

            mappings = connector.mappings.all()
            if not mappings.exists():
                return

            for mapping in mappings:
                # Calculate the total quantity change: per-meal quantity * order item quantity
                quantity_change = mapping.quantity * instance.quantity
                # For removal, use 'sold'; for addition (reversal) use the 'return' reason.
                reason = 'sold' if operation == 'remove' else 'return'
                # Calculate the price for the inventory record.
                price = round(mapping.price * quantity_change, 3)
                
                # Validate that we have required data
                if not mapping.inventory_item:
                    print(f"Warning: No inventory item found for mapping {mapping.id}")
                    continue
                    
                InventoryRecord.objects.create(
                    inventory_item=mapping.inventory_item,
                    quantity=quantity_change,
                    record_type=operation,
                    reason=reason,
                    price=price
                )
        except Exception as error:
            print(f"Error processing inventory mappings for {operation}: {error}")
            # Consider logging this error properly in production

    @staticmethod
    def pre_save(sender, instance, **kwargs):
        """
        Capture the old confirmed value so that we can compare it in post_save.
        For new instances, assume confirmed is False.
        """
        if instance.pk:
            try:
                old_instance = OrderItem.objects.get(pk=instance.pk)
                instance._old_confirmed = old_instance.confirmed
                instance._old_quantity = old_instance.quantity
            except OrderItem.DoesNotExist:
                instance._old_confirmed = False
                instance._old_quantity = 0
        else:
            instance._old_confirmed = False
            instance._old_quantity = 0

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        """
        Update inventory based on changes to the OrderItem 'confirmed' field and quantity changes.

        CASE 1: New confirmed OrderItem - subtract inventory.
        CASE 2: Updated OrderItem:
          - Transition from unconfirmed to confirmed: subtract inventory.
          - Transition from confirmed to unconfirmed: add inventory back (recorded as a return).
          - Quantity change on confirmed item: adjust inventory accordingly.
        """
        try:
            if created and instance.confirmed:
                OrderItemInventoryManager._process_mappings(instance, 'remove')
            elif not created:
                old_confirmed = getattr(instance, '_old_confirmed', False)
                old_quantity = getattr(instance, '_old_quantity', 0)
                
                # Transition from unconfirmed to confirmed.
                if instance.confirmed and not old_confirmed:
                    OrderItemInventoryManager._process_mappings(instance, 'remove')
                # Transition from confirmed to unconfirmed.
                elif not instance.confirmed and old_confirmed:
                    OrderItemInventoryManager._process_mappings(instance, 'add')
                # Handle quantity changes for confirmed items
                elif instance.confirmed and old_confirmed and instance.quantity != old_quantity:
                    # Create a temporary instance with the difference to process
                    quantity_diff = instance.quantity - old_quantity
                    if quantity_diff != 0:
                        # Create a temporary instance to process the difference
                        temp_instance = type(instance)(
                            meal=instance.meal,
                            quantity=abs(quantity_diff),
                            confirmed=True
                        )
                        if quantity_diff > 0:
                            # Increased quantity - remove more from inventory
                            OrderItemInventoryManager._process_mappings(temp_instance, 'remove')
                        else:
                            # Decreased quantity - add back to inventory
                            OrderItemInventoryManager._process_mappings(temp_instance, 'add')
        except Exception as error:
            print("Error updating inventory on order item save:", error)

    @staticmethod
    def post_delete(sender, instance, **kwargs):
        """
        When a confirmed OrderItem is deleted, add its deducted inventory back
        (recorded as a return).
        """
        try:
            if instance.confirmed:
                OrderItemInventoryManager._process_mappings(instance, 'add')
        except Exception as error:
            print("Error restoring inventory on order item deletion:", error)
