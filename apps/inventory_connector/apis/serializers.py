from rest_framework import serializers
from inventory.models import InventoryItem, InventryCategory, Supplier

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'name', 'category', 'unit', 'supplier', 
            'created_at', 'updated_at'
        ]
    
    def to_representation(self, instance):
        repr = super().to_representation(instance)
        repr['category_name'] = instance.category.name if instance.category else None
        repr['supplier_name'] = instance.supplier.name if instance.supplier else None
        return repr
