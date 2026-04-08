from rest_framework import serializers

from apps.printers.models import Printer


class PrinterSerializer(serializers.ModelSerializer):
    """Printer list və detail üçün serializer"""
    
    class Meta:
        model = Printer
        fields = ['id', 'name', 'ip_address', 'port', 'description', 'is_main']
        read_only_fields = ['id']


class PrinterCreateSerializer(serializers.ModelSerializer):
    """Printer yaratmaq üçün serializer"""
    
    class Meta:
        model = Printer
        fields = ['name', 'ip_address', 'port', 'description', 'is_main']
    
    def validate_ip_address(self, value):
        """IP adress validasiyası"""
        # IP addressin unikallığını yoxla
        if Printer.objects.filter(ip_address=value).exists():
            raise serializers.ValidationError("Bu IP address artıq istifadə olunur.")
        return value
    
    def validate(self, attrs):
        """Əgər is_main=True olarsa, digər printerlərin is_main-ini False et"""
        if attrs.get('is_main', False):
            # Əgər yeni printer main olarsa, köhnə mainləri False et
            Printer.objects.filter(is_main=True).update(is_main=False)
        return attrs


class PrinterUpdateSerializer(serializers.ModelSerializer):
    """Printer yeniləmək üçün serializer"""
    
    class Meta:
        model = Printer
        fields = ['name', 'ip_address', 'port', 'description', 'is_main']
    
    def validate_ip_address(self, value):
        """IP adress validasiyası (özündən başqa)"""
        printer_id = self.instance.id if self.instance else None
        if Printer.objects.filter(ip_address=value).exclude(id=printer_id).exists():
            raise serializers.ValidationError("Bu IP address artıq istifadə olunur.")
        return value
    
    def validate(self, attrs):
        """Əgər is_main=True olarsa, digər printerlərin is_main-ini False et"""
        if attrs.get('is_main', False):
            # Əgər bu printer main olarsa, digər mainləri False et
            Printer.objects.filter(is_main=True).exclude(id=self.instance.id).update(is_main=False)
        return attrs
