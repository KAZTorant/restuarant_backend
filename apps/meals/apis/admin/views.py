from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.meals.apis.admin.serializers import (
    AdminMealCategoryDetailSerializer, AdminMealCategorySerializer,
    AdminMealGroupDetailSerializer, AdminMealGroupSerializer,
    AdminMealSerializer, AdminPreparationPlaceDetailSerializer,
    AdminPreparationPlaceSerializer)
from apps.meals.models import Meal, MealCategory
from apps.meals.models.meal import MealGroup
from apps.printers.models.place import PreparationPlace
from apps.users.permissions import IsAdmin, IsAdminPanelUser, IsRestaurantOwner


class AdminRequiredMixin:
    """Superuser, staff, admin və ya restaurant owner tələb edir"""
    permission_classes = [IsAdminPanelUser]


# ─────────────────────────────────────────────
#  PREPARATION PLACES  (Hazırlanma Yerləri)
# ─────────────────────────────────────────────

class AdminPreparationPlaceListCreateAPIView(AdminRequiredMixin, generics.ListCreateAPIView):
    """
    GET  → Bütün hazırlanma yerlərinin siyahısı
    POST → Yeni hazırlanma yeri yarat
    """
    queryset = PreparationPlace.objects.select_related("printer").order_by("name")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["id", "name"]

    def get_serializer_class(self):
        return AdminPreparationPlaceDetailSerializer


class AdminPreparationPlaceRetrieveUpdateDestroyAPIView(AdminRequiredMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → Hazırlanma yeri detalları
    PUT    → Tam yenilə
    PATCH  → Qismən yenilə
    DELETE → Sil
    """
    queryset = PreparationPlace.objects.select_related("printer")
    serializer_class = AdminPreparationPlaceDetailSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Check meals using this preparation place (many-to-many)
        meal_count = instance.meals_multi.count()
        # Also check the deprecated single preparation_place field
        meal_count_single = instance.meals_single.count()
        total_meals = meal_count + meal_count_single
        
        if total_meals > 0:
            return Response(
                {
                    "error": f"Bu hazırlanma yerinin {total_meals} yeməyi var. "
                             "Əvvəlcə yeməklərdən çıxarın."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
#  MEAL GROUP  (Yemək kateqoriyası qrupları)
# ─────────────────────────────────────────────

class AdminMealGroupListCreateAPIView(AdminRequiredMixin, generics.ListCreateAPIView):
    """
    GET  → Bütün qrupların siyahısı (axtarış dəstəklənir)
    POST → Yeni qrup yarat
    """
    queryset = MealGroup.objects.all().order_by("id")
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["id", "name", "created_at"]

    def get_serializer_class(self):
        return AdminMealGroupSerializer


class AdminMealGroupRetrieveUpdateDestroyAPIView(AdminRequiredMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → Qrup detalları (kateqoriya sayı ilə)
    PUT    → Tam yenilə
    PATCH  → Qismən yenilə
    DELETE → Sil
    """
    queryset = MealGroup.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdminMealGroupDetailSerializer
        return AdminMealGroupSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        category_count = instance.categories.count()
        if category_count > 0:
            return Response(
                {
                    "error": f"Bu qrupun {category_count} kateqoriyası var. "
                             "Əvvəlcə kateqoriyaları silin və ya başqa qrupa köçürün."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
#  MEAL CATEGORY  (Yemək kateqoriyaları)
# ─────────────────────────────────────────────

class AdminMealCategoryListCreateAPIView(AdminRequiredMixin, generics.ListCreateAPIView):
    """
    GET  → Bütün kateqoriyaların siyahısı
           Query params: ?group_id=  ?is_extra=true/false
    POST → Yeni kateqoriya yarat
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["id", "name", "created_at"]
    serializer_class = AdminMealCategorySerializer

    def get_queryset(self):
        queryset = MealCategory.objects.select_related("group").order_by("id")
        group_id = self.request.query_params.get("group_id")
        is_extra = self.request.query_params.get("is_extra")

        if group_id:
            queryset = queryset.filter(group_id=group_id)
        if is_extra is not None:
            queryset = queryset.filter(is_extra=is_extra.lower() == "true")
        return queryset


class AdminMealCategoryRetrieveUpdateDestroyAPIView(AdminRequiredMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → Kateqoriya detalları (yemək sayı ilə)
    PUT    → Tam yenilə
    PATCH  → Qismən yenilə
    DELETE → Sil
    """
    queryset = MealCategory.objects.select_related("group")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdminMealCategoryDetailSerializer
        return AdminMealCategorySerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        meal_count = instance.meals.count()
        if meal_count > 0:
            return Response(
                {
                    "error": f"Bu kateqoriyanın {meal_count} yeməyi var. "
                             "Əvvəlcə yeməkləri silin və ya başqa kateqoriyaya köçürün."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
#  MEAL  (Yeməklər)
# ─────────────────────────────────────────────

class AdminMealListCreateAPIView(AdminRequiredMixin, generics.ListCreateAPIView):
    """
    GET  → Bütün yeməklərin siyahısı
           Query params: ?category_id=  ?group_id=  ?search=  ?is_extra=true/false
    POST → Yeni yemək yarat
    """
    serializer_class = AdminMealSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "category__name"]
    ordering_fields = ["id", "name", "price", "created_at"]

    def get_queryset(self):
        queryset = (
            Meal.objects
            .select_related("category", "category__group", "preparation_place")
            .prefetch_related("preparation_places", "inventory_connector__mappings")
            .order_by("id")
        )
        category_id = self.request.query_params.get("category_id")
        group_id = self.request.query_params.get("group_id")
        is_extra = self.request.query_params.get("is_extra")

        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if group_id:
            queryset = queryset.filter(category__group_id=group_id)
        if is_extra is not None:
            queryset = queryset.filter(category__is_extra=is_extra.lower() == "true")
        return queryset


class AdminMealRetrieveUpdateDestroyAPIView(AdminRequiredMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → Yemək detalları (qiymət, marja, hazırlanma yerləri, inventory)
    PUT    → Tam yenilə
    PATCH  → Qismən yenilə (məs. yalnız qiyməti yenilə)
    DELETE → Sil
    """
    serializer_class = AdminMealSerializer
    queryset = (
        Meal.objects
        .select_related("category", "category__group", "preparation_place")
        .prefetch_related("preparation_places", "inventory_connector__mappings")
    )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Aktiv sifariş yoxlanışı
        active_order_items = instance.orderitem_set.filter(
            order__is_paid=False,
            order__is_deleted=False
        )
        if active_order_items.exists():
            return Response(
                {"error": "Bu yemək aktiv sifarişdə var. Silinə bilməz."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminMealBulkUpdatePriceAPIView(AdminRequiredMixin, APIView):
    """
    POST → Bir neçə yeməyin qiymətini eyni anda yenilə
    Body: { "meals": [{"id": 1, "price": 5.50}, {"id": 2, "price": 8.00}] }
    """
    def post(self, request):
        meals_data = request.data.get("meals", [])
        if not meals_data:
            return Response(
                {"error": "meals siyahısı boş ola bilməz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = []
        errors = []
        for item in meals_data:
            meal_id = item.get("id")
            price = item.get("price")
            if meal_id is None or price is None:
                errors.append({"item": item, "error": "id və price tələb olunur."})
                continue
            try:
                meal = Meal.objects.get(id=meal_id)
                meal.price = price
                meal.save(update_fields=["price"])
                updated.append({"id": meal_id, "price": price})
            except Meal.DoesNotExist:
                errors.append({"id": meal_id, "error": "Yemək tapılmadı."})

        return Response(
            {"updated": updated, "errors": errors},
            status=status.HTTP_200_OK,
        )


class AdminMealBulkUpdateCategoryAPIView(AdminRequiredMixin, APIView):
    """
    POST → Bir neçə yeməyin kateqoriyasını eyni anda dəyiş
    Body: { "meal_ids": [1, 2, 3], "category_id": 5 }
    """
    def post(self, request):
        meal_ids = request.data.get("meal_ids", [])
        category_id = request.data.get("category_id")

        if not meal_ids:
            return Response(
                {"error": "meal_ids siyahısı boş ola bilməz."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        category = get_object_or_404(MealCategory, id=category_id)
        updated_count = Meal.objects.filter(id__in=meal_ids).update(category=category)

        return Response(
            {
                "updated_count": updated_count,
                "category_id": category.id,
                "category_name": category.name,
            },
            status=status.HTTP_200_OK,
        )


class AdminMealBulkUpdatePreparationPlacesAPIView(AdminRequiredMixin, APIView):
    """
    POST → Bir neçə yeməyin hazırlanma yerlərini eyni anda dəyiş
    Body: { "meal_ids": [1, 2, 3], "preparation_place_ids": [1, 2] }
    """
    def post(self, request):
        meal_ids = request.data.get("meal_ids", [])
        place_ids = request.data.get("preparation_place_ids", [])

        if not meal_ids:
            return Response(
                {"error": "meal_ids siyahısı boş ola bilməz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        meals = Meal.objects.filter(id__in=meal_ids)
        updated = []
        for meal in meals:
            meal.preparation_places.set(place_ids)
            updated.append(meal.id)

        return Response(
            {"updated_meal_ids": updated, "preparation_place_ids": place_ids},
            status=status.HTTP_200_OK,
        )
