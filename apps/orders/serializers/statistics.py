from rest_framework import serializers
from apps.orders.models import Statistics


class WithdrawnInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying withdrawn amounts and notes from closed shifts.
    """
    started_by_username = serializers.CharField(source='started_by.username', read_only=True)
    started_by_full_name = serializers.SerializerMethodField()
    ended_by_username = serializers.CharField(source='ended_by.username', read_only=True)
    ended_by_full_name = serializers.SerializerMethodField()
    shift_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Statistics
        fields = [
            'id',
            'started_by_username',
            'started_by_full_name',
            'start_time',
            'ended_by_username',
            'ended_by_full_name',
            'end_time',
            'shift_duration',
            'initial_cash',
            'cash_total',
            'card_total',
            'other_total',
            'total',
            'withdrawn_amount',
            'withdrawn_notes',
            'remaining_cash',
            'date',
        ]
    
    def get_started_by_full_name(self, obj):
        """Get full name of the user who started the shift"""
        if obj.started_by:
            full_name = f"{obj.started_by.first_name} {obj.started_by.last_name}".strip()
            return full_name if full_name else obj.started_by.username
        return None
    
    def get_ended_by_full_name(self, obj):
        """Get full name of the user who ended the shift"""
        if obj.ended_by:
            full_name = f"{obj.ended_by.first_name} {obj.ended_by.last_name}".strip()
            return full_name if full_name else obj.ended_by.username
        return None
    
    def get_shift_duration(self, obj):
        """Calculate shift duration in hours"""
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            hours = duration.total_seconds() / 3600
            return round(hours, 2)
        return None


class StatisticsSummarySerializer(serializers.ModelSerializer):
    """
    Basic serializer for Statistics list view.
    """
    started_by_username = serializers.CharField(source='started_by.username', read_only=True)
    ended_by_username = serializers.CharField(source='ended_by.username', read_only=True)
    
    class Meta:
        model = Statistics
        fields = [
            'id',
            'started_by_username',
            'start_time',
            'ended_by_username',
            'end_time',
            'total',
            'withdrawn_amount',
            'is_closed',
            'date',
        ]
