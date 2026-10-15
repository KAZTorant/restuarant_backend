from rest_framework import serializers

from apps.tables.models import Table
from apps.tables.models import Room


class TableSerializer(serializers.ModelSerializer):
    """Table list item.

    ``TableAPIView`` prefetches each table's unpaid, non-deleted orders into
    ``open_orders_cache`` so a whole hall is serialized without per-table
    queries. When the cache is missing (serializer used elsewhere) the model
    properties are used, which gives the same result with more queries.
    """

    waitress = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    print_check = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = (
            "id",
            "number",
            "room",
            "waitress",
            "total_price",
            "print_check",
        )

    @staticmethod
    def _current_order(obj: Table):
        """Same as ``Table.current_order`` (first unpaid main order)."""
        cached = getattr(obj, "open_orders_cache", None)
        if cached is None:
            return obj.current_order
        return next((order for order in cached if order.is_main), None)

    def get_waitress(self, obj: Table):
        order = self._current_order(obj)
        waitress = order.waitress if order else None
        if not waitress:
            return {
                "name": "",
                "id": 0,
            }

        return {
            "name": waitress.get_full_name(),
            "id": waitress.id,
        }

    def get_total_price(self, obj: Table):
        """Same as ``Table.total_price`` (sum of all unpaid orders)."""
        cached = getattr(obj, "open_orders_cache", None)
        if cached is None:
            return obj.total_price
        price = 0
        for order in cached:
            price += order.total_price
        return price

    def get_print_check(self, obj: Table):
        order = self._current_order(obj)
        return order.is_check_printed if order else False


class TableDetailSerializer(serializers.ModelSerializer):

    waitress = serializers.SerializerMethodField()
    print_check = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = (
            "id",
            "number",
            "room",
            "waitress",
            "total_price",
            "print_check",
        )

    def get_waitress(self, obj: Table):
        if not obj.waitress:
            return {
                "name": self.context['user'].get_full_name(),
                "id": 0,
            }

        return {
            "name": obj.waitress.get_full_name(),
            "id": obj.waitress.id,
        }

    def get_print_check(self, obj: Table):
        return obj.current_order.is_check_printed if obj.current_order else False


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = (
            "id",
            "name",
            "description"
        )
