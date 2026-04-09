from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.deletion import ProtectedError
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.apis.admin.serializers import (AdminGroupDetailSerializer,
                                               AdminGroupListSerializer,
                                               AdminGroupWriteSerializer,
                                               AdminPermissionSerializer,
                                               AdminUserCreateSerializer,
                                               AdminUserDetailSerializer,
                                               AdminUserListSerializer,
                                               AdminUserSetPasswordSerializer,
                                               AdminUserUpdateSerializer)
from apps.users.auth import AdminTokenAuthentication
from apps.users.models import User
from apps.users.permissions import IsAdminPanelUser


class AdminRequiredMixin:
    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAdminPanelUser]


# ─────────────────────────────────────────────
#  PERMISSIONS — read-only list (group assign üçün)
# ─────────────────────────────────────────────

class AdminPermissionListAPIView(AdminRequiredMixin, generics.ListAPIView):
    """
    GET → Bütün permissions (qrup yaradarkən seçim üçün)
    Filter: ?app_label=payments  qruplandırmaq üçün
    """
    serializer_class = AdminPermissionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "codename", "content_type__app_label", "content_type__model"]
    pagination_class = None  # Hamısı bir anda qaytarılır (152 qeyd)

    def get_queryset(self):
        qs = Permission.objects.select_related("content_type").order_by(
            "content_type__app_label", "codename"
        )
        app_label = self.request.query_params.get("app_label")
        if app_label:
            qs = qs.filter(content_type__app_label=app_label)
        return qs


# ─────────────────────────────────────────────
#  GROUPS
# ─────────────────────────────────────────────

class AdminGroupListCreateAPIView(AdminRequiredMixin, generics.ListCreateAPIView):
    """
    GET  → Qrupların siyahısı (pagination + axtarış)
    POST → Yeni qrup yarat (name + permission ID-ləri ilə)
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["id", "name"]
    ordering = ["id"]

    def get_queryset(self):
        return Group.objects.prefetch_related("permissions").all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminGroupWriteSerializer
        return AdminGroupListSerializer

    def create(self, request, *args, **kwargs):
        serializer = AdminGroupWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        return Response(
            AdminGroupDetailSerializer(group).data,
            status=status.HTTP_201_CREATED,
        )


class AdminGroupRetrieveUpdateDestroyAPIView(AdminRequiredMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → Qrup detalları (tam permissions siyahısı)
    PUT    → Tam yenilə
    PATCH  → Qismən yenilə
    DELETE → Sil
    """
    queryset = Group.objects.prefetch_related("permissions__content_type").all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdminGroupDetailSerializer
        return AdminGroupWriteSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = AdminGroupWriteSerializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        return Response(AdminGroupDetailSerializer(group).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user_count = instance.user_set.count()
        if user_count > 0:
            return Response(
                {
                    "error": f"Bu qrupda {user_count} istifadəçi var. "
                             "Əvvəlcə istifadəçiləri qrupdan çıxarın."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
#  USERS
# ─────────────────────────────────────────────

class AdminUserListCreateAPIView(AdminRequiredMixin, generics.ListCreateAPIView):
    """
    GET  → İstifadəçilərin siyahısı (pagination + filter + axtarış)
    POST → Yeni istifadəçi yarat
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["username", "first_name", "last_name", "email"]
    ordering_fields = ["id", "username", "date_joined"]
    ordering = ["id"]

    def get_queryset(self):
        qs = User.objects.prefetch_related("groups").order_by("id")

        params = self.request.query_params

        # Filter: type (waitress, admin, restaurant, ...)
        user_type = params.get("type")
        if user_type:
            qs = qs.filter(type=user_type)

        # Filter: is_staff
        is_staff = params.get("is_staff")
        if is_staff is not None:
            qs = qs.filter(is_staff=is_staff.lower() == "true")

        # Filter: is_active
        is_active = params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        # Filter: group_id
        group_id = params.get("group_id")
        if group_id:
            qs = qs.filter(groups__id=group_id)

        return qs

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminUserCreateSerializer
        return AdminUserListSerializer

    def create(self, request, *args, **kwargs):
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            AdminUserDetailSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class AdminUserRetrieveUpdateDestroyAPIView(AdminRequiredMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → İstifadəçi detalları (groups + permissions)
    PUT    → Tam yenilə
    PATCH  → Qismən yenilə
    DELETE → Sil (superuser silinə bilməz)
    """
    queryset = User.objects.prefetch_related(
        "groups", "user_permissions__content_type"
    ).all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdminUserDetailSerializer
        return AdminUserUpdateSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = AdminUserUpdateSerializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(AdminUserDetailSerializer(user).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_superuser:
            return Response(
                {"error": "Superuser istifadəçi silinə bilməz."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if instance == request.user:
            return Response(
                {"error": "Özünüzü silə bilməzsiniz."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            instance.delete()
        except ProtectedError as e:
            # Tarixə aid qeydlər (növbə, statistika və s.) bu istifadəçiyə bağlıdır.
            # Silmək əvəzinə is_active=False etmək tövsiyə olunur.
            return Response(
                {
                    "error": (
                        "Bu istifadəçi silinə bilməz, çünki ona bağlı tarix qeydləri var "
                        "(növbə/statistika). Əvəzinə istifadəçini deaktiv edin: "
                        "PATCH /api/admin/users/users/{id}/ — {\"is_active\": false}"
                    ),
                    "detail": str(e).split("'")[0].strip(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserSetPasswordAPIView(AdminRequiredMixin, APIView):
    """
    POST /api/admin/users/{id}/set-password/
    İstifadəçinin şifrəsini dəyişdir.
    Yalnız superuser istənilən istifadəçinin şifrəsini dəyişə bilər.
    Admin/restaurant öz şifrəsini dəyişə bilər.
    """

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def post(self, request, pk):
        target = self.get_object(pk)
        if not target:
            return Response(
                {"detail": "İstifadəçi tapılmadı."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Yalnız superuser başqasının şifrəsini dəyişə bilər
        if target != request.user and not request.user.is_superuser:
            return Response(
                {"detail": "Yalnız superuser başqa istifadəçinin şifrəsini dəyişə bilər."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AdminUserSetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target.set_password(serializer.validated_data["password"])
        target.save(update_fields=["password"])
        return Response({"detail": "Şifrə uğurla dəyişdirildi."})
