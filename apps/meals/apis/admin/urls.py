from django.urls import path

from apps.meals.apis.admin.views import (  # Preparation Places; Meal Group; Meal Category; Meal; Bulk Actions
    AdminMealBulkUpdateCategoryAPIView,
    AdminMealBulkUpdatePreparationPlacesAPIView,
    AdminMealBulkUpdatePriceAPIView, AdminMealCategoryListCreateAPIView,
    AdminMealCategoryRetrieveUpdateDestroyAPIView,
    AdminMealGroupListCreateAPIView,
    AdminMealGroupRetrieveUpdateDestroyAPIView, AdminMealListCreateAPIView,
    AdminMealRetrieveUpdateDestroyAPIView,
    AdminPreparationPlaceListCreateAPIView,
    AdminPreparationPlaceRetrieveUpdateDestroyAPIView)

urlpatterns = [
    # ── Preparation Places ────────────────────────────────────
    path(
        "preparation-places/",
        AdminPreparationPlaceListCreateAPIView.as_view(),
        name="admin-preparation-place-list-create",
    ),
    path(
        "preparation-places/<int:pk>/",
        AdminPreparationPlaceRetrieveUpdateDestroyAPIView.as_view(),
        name="admin-preparation-place-detail",
    ),

    # ── Meal Groups ──────────────────────────────────────────
    path(
        "groups/",
        AdminMealGroupListCreateAPIView.as_view(),
        name="admin-meal-group-list-create",
    ),
    path(
        "groups/<int:pk>/",
        AdminMealGroupRetrieveUpdateDestroyAPIView.as_view(),
        name="admin-meal-group-detail",
    ),

    # ── Meal Categories ───────────────────────────────────────
    path(
        "categories/",
        AdminMealCategoryListCreateAPIView.as_view(),
        name="admin-meal-category-list-create",
    ),
    path(
        "categories/<int:pk>/",
        AdminMealCategoryRetrieveUpdateDestroyAPIView.as_view(),
        name="admin-meal-category-detail",
    ),

    # ── Meals ─────────────────────────────────────────────────
    path(
        "meals/",
        AdminMealListCreateAPIView.as_view(),
        name="admin-meal-list-create",
    ),
    path(
        "meals/<int:pk>/",
        AdminMealRetrieveUpdateDestroyAPIView.as_view(),
        name="admin-meal-detail",
    ),

    # ── Bulk Actions ──────────────────────────────────────────
    path(
        "meals/bulk/update-price/",
        AdminMealBulkUpdatePriceAPIView.as_view(),
        name="admin-meal-bulk-update-price",
    ),
    path(
        "meals/bulk/update-category/",
        AdminMealBulkUpdateCategoryAPIView.as_view(),
        name="admin-meal-bulk-update-category",
    ),
    path(
        "meals/bulk/update-preparation-places/",
        AdminMealBulkUpdatePreparationPlacesAPIView.as_view(),
        name="admin-meal-bulk-update-preparation-places",
    ),
]
