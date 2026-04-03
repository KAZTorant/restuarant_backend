from rest_framework import serializers

from apps.meals.models import Meal, MealCategory
from apps.meals.models.meal import MealGroup
from apps.printers.models.place import PreparationPlace


class AdminPreparationPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreparationPlace
        fields = ("id", "name")


class AdminMealGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealGroup
        fields = ("id", "name", "description", "created_at", "updated_at")


class AdminMealGroupDetailSerializer(serializers.ModelSerializer):
    """MealGroup with nested categories"""
    categories_count = serializers.SerializerMethodField()

    class Meta:
        model = MealGroup
        fields = ("id", "name", "description", "categories_count", "created_at", "updated_at")

    def get_categories_count(self, obj):
        return obj.categories.count()


class AdminMealCategorySerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = MealCategory
        fields = (
            "id",
            "name",
            "description",
            "group",
            "group_name",
            "is_extra",
            "created_at",
            "updated_at",
        )


class AdminMealCategoryDetailSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)
    meals_count = serializers.SerializerMethodField()

    class Meta:
        model = MealCategory
        fields = (
            "id",
            "name",
            "description",
            "group",
            "group_name",
            "is_extra",
            "meals_count",
            "created_at",
            "updated_at",
        )

    def get_meals_count(self, obj):
        return obj.meals.count()


class AdminMealSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    group_name = serializers.CharField(source="category.group.name", read_only=True)
    preparation_places = AdminPreparationPlaceSerializer(many=True, read_only=True)
    preparation_place_ids = serializers.PrimaryKeyRelatedField(
        queryset=PreparationPlace.objects.all(),
        many=True,
        write_only=True,
        source="preparation_places",
        required=False,
    )
    is_extra = serializers.BooleanField(read_only=True)
    cost_price = serializers.SerializerMethodField()
    marja_amount = serializers.SerializerMethodField()
    marja_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Meal
        fields = (
            "id",
            "name",
            "description",
            "price",
            "category",
            "category_name",
            "group_name",
            "preparation_places",
            "preparation_place_ids",
            "is_extra",
            "cost_price",
            "marja_amount",
            "marja_percentage",
            "created_at",
            "updated_at",
        )

    def get_cost_price(self, obj):
        try:
            connector = obj.inventory_connector
            total_cost = sum(
                mapping.quantity * mapping.price
                for mapping in connector.mappings.all()
            )
            return round(float(total_cost), 2)
        except Exception:
            return 0.00

    def get_marja_amount(self, obj):
        try:
            connector = obj.inventory_connector
            total_cost = sum(
                mapping.quantity * mapping.price
                for mapping in connector.mappings.all()
            )
            return round(float(obj.price - total_cost), 2)
        except Exception:
            return round(float(obj.price), 2)

    def get_marja_percentage(self, obj):
        try:
            connector = obj.inventory_connector
            total_cost = sum(
                mapping.quantity * mapping.price
                for mapping in connector.mappings.all()
            )
            if obj.price > 0:
                return round(float((obj.price - total_cost) / obj.price * 100), 1)
            return 0.0
        except Exception:
            return 100.0

    def create(self, validated_data):
        preparation_places = validated_data.pop("preparation_places", [])
        meal = Meal.objects.create(**validated_data)
        if preparation_places:
            meal.preparation_places.set(preparation_places)
        return meal

    def update(self, instance, validated_data):
        preparation_places = validated_data.pop("preparation_places", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if preparation_places is not None:
            instance.preparation_places.set(preparation_places)
        return instance
        return instance
