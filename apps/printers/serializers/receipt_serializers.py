from rest_framework import serializers

from apps.printers.models import Receipt


class ReceiptSerializer(serializers.ModelSerializer):
    """Receipt list üçün serializer"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    orders_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'created_at', 'type', 'type_display', 
            'printer_response_status_code', 'orders_count'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_orders_count(self, obj):
        """Sifarişlərin sayı"""
        return obj.orders.count()


class ReceiptDetailSerializer(serializers.ModelSerializer):
    """Receipt detail üçün serializer"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    orders_list = serializers.SerializerMethodField()
    payment_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = Receipt
        fields = [
            'id', 'created_at', 'type', 'type_display', 
            'text', 'orders_list', 'payment_detail', 
            'printer_response_status_code'
        ]
        read_only_fields = ['id', 'created_at', 'text', 'printer_response_status_code']
    
    def get_orders_list(self, obj):
        """Sifarişlərin ID-ləri"""
        return list(obj.orders.values_list('id', flat=True))
    
    def get_payment_detail(self, obj):
        """Ödəniş məlumatı"""
        if obj.payment:
            return {
                'id': obj.payment.id,
                'amount': float(obj.payment.amount) if hasattr(obj.payment, 'amount') else None,
            }
        return None
