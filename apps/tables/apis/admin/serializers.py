from rest_framework import serializers

from apps.tables.models import Room, Table

# ─────────────────────────────────────────────
#  ROOM (Zal) Serializers
# ─────────────────────────────────────────────

class AdminRoomSerializer(serializers.ModelSerializer):
    """Sadə serializer — siyahı, yarat, yenilə"""

    class Meta:
        model = Room
        fields = ("id", "name", "description", "is_active", "created_at", "updated_at")


class AdminRoomDetailSerializer(serializers.ModelSerializer):
    """Detal serializer — tables_count əlavə edir"""
    tables_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = (
            "id",
            "name",
            "description",
            "is_active",
            "tables_count",
            "created_at",
            "updated_at",
        )

    def get_tables_count(self, obj):
        return obj.tables.count()


# ─────────────────────────────────────────────
#  TABLE (Stol) Serializers
# ─────────────────────────────────────────────

class AdminTableRoomSerializer(serializers.ModelSerializer):
    """Nested room üçün sadə serializer"""

    class Meta:
        model = Room
        fields = ("id", "name")


class AdminTableSerializer(serializers.ModelSerializer):
    """Siyahı, yarat, yenilə"""
    room_name = serializers.CharField(source="room.name", read_only=True)

    class Meta:
        model = Table
        fields = ("id", "number", "capacity", "room", "room_name", "created_at", "updated_at")


class AdminTableDetailSerializer(serializers.ModelSerializer):
    """Detal görünüşü — nested room + cari sifariş məlumatı"""
    room_name = serializers.CharField(source="room.name", read_only=True)
    is_occupied = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = (
            "id",
            "number",
            "capacity",
            "room",
            "room_name",
            "is_occupied",
            "total_price",
            "created_at",
            "updated_at",
        )

    def get_is_occupied(self, obj):
        return not obj.assignable_table

    def get_total_price(self, obj):
        return obj.total_price
