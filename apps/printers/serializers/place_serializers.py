from rest_framework import serializers
from apps.printers.models import PreparationPlace
from apps.printers.serializers.printer_serializers import PrinterSerializer


class PreparationPlaceSerializer(serializers.ModelSerializer):
    """PreparationPlace list və detail üçün serializer"""
    printer_detail = PrinterSerializer(source='printer', read_only=True)
    
    class Meta:
        model = PreparationPlace
        fields = ['id', 'name', 'printer', 'printer_detail']
        read_only_fields = ['id']


class PreparationPlaceCreateSerializer(serializers.ModelSerializer):
    """PreparationPlace yaratmaq üçün serializer"""
    
    class Meta:
        model = PreparationPlace
        fields = ['name', 'printer']
    
    def validate_name(self, value):
        """Adın unikallığını yoxla"""
        if PreparationPlace.objects.filter(name=value).exists():
            raise serializers.ValidationError("Bu adda hazırlanma yeri artıq mövcuddur.")
        return value


class PreparationPlaceUpdateSerializer(serializers.ModelSerializer):
    """PreparationPlace yeniləmək üçün serializer"""
    
    class Meta:
        model = PreparationPlace
        fields = ['name', 'printer']
    
    def validate_name(self, value):
        """Adın unikallığını yoxla (özündən başqa)"""
        place_id = self.instance.id if self.instance else None
        if PreparationPlace.objects.filter(name=value).exclude(id=place_id).exists():
            raise serializers.ValidationError("Bu adda hazırlanma yeri artıq mövcuddur.")
        return value
