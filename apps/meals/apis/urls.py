from django.urls import path
from apps.meals.apis import MealCategoryAPIView
from apps.meals.apis import MealAPIView
from apps.meals.apis.meals import MealGroupAPIView

urlpatterns = [
    path("categories/", MealCategoryAPIView.as_view()),
    path("groups/", MealGroupAPIView.as_view()),
    path("meals/", MealAPIView.as_view()),
]
