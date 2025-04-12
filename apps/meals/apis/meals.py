from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import ListAPIView

from apps.meals.models import Meal
from apps.meals.models import MealCategory
from apps.meals.serializers import MealSerializer
from apps.meals.serializers import MealCategorySerializer


class MealCategoryAPIView(ListAPIView):
    model = MealCategory
    serializer_class = MealCategorySerializer
    queryset = MealCategory.objects.all()

    @method_decorator(cache_page(settings.CACHE_TIME_IN_SECONDS))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MealAPIView(ListAPIView):
    model = Meal
    serializer_class = MealSerializer

    # Define your query parameter for the swagger documentation
    meal_category_id_param = openapi.Parameter(
        'meal_category_id',
        openapi.IN_QUERY,
        description="Filter meals by the meal category ID",
        type=openapi.TYPE_INTEGER
    )

    @method_decorator(cache_page(settings.CACHE_TIME_IN_SECONDS))
    @swagger_auto_schema(manual_parameters=[meal_category_id_param])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        meal_category_id = self.request.GET.get("meal_category_id", 0)
        if meal_category_id:
            return Meal.objects.filter(category__id=meal_category_id)
        return Meal.objects.filter(category__isnull=True)
