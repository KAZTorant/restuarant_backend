from rest_framework import serializers

from apps.meals.models import Meal
from apps.meals.models import MealCategory
from apps.meals.models.meal import MealGroup


class MealCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MealCategory
        fields = (
            "id",
            "name",
            "description",
        )


class MealGroupSerializer(serializers.ModelSerializer):
    categories = MealCategorySerializer(many=True)

    class Meta:
        model = MealGroup
        fields = (
            "id",
            "name",
            "description",
            "categories",
        )


class MealSerializer(serializers.ModelSerializer):
    is_extra = serializers.SerializerMethodField()

    class Meta:
        model = Meal
        fields = (
            "id",
            "name",
            "description",
            "price",
            "is_extra",
        )

    def get_is_extra(self, meal: Meal):
        return meal.category.is_extra if meal.category else False
