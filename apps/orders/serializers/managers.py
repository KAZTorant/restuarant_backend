from rest_framework import serializers
from apps.meals.models import Meal
from apps.orders.models import Order
from apps.orders.models import OrderItem
from apps.orders.models import OrderItemDeletionLog
from apps.users.models import User


class DeleteOrderItemV2Serializer(serializers.Serializer):
    order_id = serializers.IntegerField(
        required=False,
        help_text="Sifarişin ID-si (varsa)"
    )
    meal_id = serializers.IntegerField(
        help_text="Silinəcək yeməyin ID-si"
    )
    order_item_id = serializers.IntegerField(
        help_text="Silinəcək extra yeməyin ID-si"
    )
    quantity = serializers.IntegerField(
        default=1,
        min_value=1,
        help_text="Azaldılacaq miqdar"
    )
    confirmed = serializers.BooleanField(default=False)

    reason = serializers.ChoiceField(
        choices=OrderItemDeletionLog.REASON_CHOICES,
        required=False,
        help_text="Təsdiqlənmiş məhsullar üçün silinmə səbəbi: 'return' və ya 'waste'"
    )
    reason_comment = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Silinmə səbəbinə əlavə izah (şərh)"
    )

    def validate_meal_id(self, value):
        try:
            Meal.objects.get(id=value)
        except Meal.DoesNotExist:
            raise serializers.ValidationError("Yemək tapılmadı.")
        return value

    def validate(self, attrs):
        order = self.context.get('order')
        meal_id = attrs.get('meal_id')
        try:
            item = OrderItem.objects.get(order=order, meal_id=meal_id)
        except OrderItem.DoesNotExist:
            raise serializers.ValidationError({
                'meal_id': "Sifariş məhsulu tapılmadı."
            })
        # require reason for confirmed items
        if item.confirmed and not attrs.get('reason'):
            raise serializers.ValidationError({
                'reason': "Təsdiqlənmiş məhsullar üçün səbəb tələb olunur."
            })
        return attrs


class DeleteOrderItemSerializer(serializers.Serializer):
    meal_id = serializers.IntegerField(
        help_text="ID of the meal to decrease quantity from"
    )
    order_id = serializers.IntegerField(
        help_text="ID of the order",
        required=False
    )

    quantity = serializers.IntegerField(
        help_text="Quantity to decrease", min_value=1, default=1
    )

    def validate_meal_id(self, value):
        # Ensure the meal exists
        try:
            Meal.objects.get(id=value)
        except Meal.DoesNotExist:
            raise serializers.ValidationError("Meal not found")
        return value

    def save(self):
        meal_id = self.validated_data.get('meal_id', 0)
        quantity_to_decrease = self.validated_data.get('quantity', 0)
        order: Order = self.context['order']

        # Try to find the order item within the order
        order_item = OrderItem.objects.filter(
            order=order,
            meal_id=meal_id
        ).first()
        if not order_item:
            raise serializers.ValidationError("Order item not found")

        # Decrease quantity or delete if necessary
        new_quantity = order_item.quantity - quantity_to_decrease
        if new_quantity > 0:
            order_item.quantity = new_quantity
            order_item.save()
        else:
            order_item.delete()
        order.refresh_from_db()
        order.update_total_price()


class ListWaitressSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
        )

    def get_full_name(self, obj: User):
        return obj.get_full_name()
