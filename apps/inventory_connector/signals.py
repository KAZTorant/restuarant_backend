
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
        connector = getattr(instance.meal, 'inventory_connector', None)
        if not connector:
            return

        mappings = connector.mappings.all()
        for mapping in mappings:
            # Calculate the total quantity change: per-meal quantity * order item quantity
            quantity_change = mapping.quantity * instance.quantity
            # For removal, use 'sold'; for addition (reversal) use the 'return' reason.
            reason = 'sold' if operation == 'remove' else 'return'
            # Calculate the price for the inventory record.
            price = round(mapping.price * quantity_change, 3)
            InventoryRecord.objects.create(
                inventory_item=mapping.inventory_item,
                quantity=quantity_change,
                record_type=operation,
                reason=reason,
                price=price
            )

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
            except OrderItem.DoesNotExist:
                instance._old_confirmed = False
        else:
            instance._old_confirmed = False

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        """
        Update inventory based on changes to the OrderItem 'confirmed' field.

        CASE 1: New confirmed OrderItem - subtract inventory.
        CASE 2: Updated OrderItem:
          - Transition from unconfirmed to confirmed: subtract inventory.
          - Transition from confirmed to unconfirmed: add inventory back (recorded as a return).
        """
        try:
            if created and instance.confirmed:
                OrderItemInventoryManager._process_mappings(instance, 'remove')
            elif not created:
                old_confirmed = getattr(instance, '_old_confirmed', False)
                # Transition from unconfirmed to confirmed.
                if instance.confirmed and not old_confirmed:
                    OrderItemInventoryManager._process_mappings(
                        instance, 'remove')
                # Transition from confirmed to unconfirmed.
                elif not instance.confirmed and old_confirmed:
                    OrderItemInventoryManager._process_mappings(
                        instance, 'add')
        except Exception as error:
            print("Error updating inventory on order item save:", error)

    @staticmethod
    def post_delete(sender, instance, **kwargs):
        """
        When a confirmed OrderItem is deleted, add its deducted inventory back
        (recorded as a return).
        """
        pass
