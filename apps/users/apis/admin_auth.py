from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.auth import AdminTokenAuthentication
from apps.users.models.token import AdminAuthToken
from apps.users.permissions import IsAdminPanelUser
from apps.users.serializers.admin_auth import (AdminLoginSerializer,
                                               AdminUserSerializer)


class AdminLoginAPIView(APIView):
    """
    POST /api/admin/auth/login/
    username + password ilə admin panelə giriş.
    Uğurlu girişdə Bearer token qaytarır.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']

        # Əvvəlki token-ləri sil (hər cihaz üçün tək aktiv token)
        AdminAuthToken.objects.filter(user=user).delete()

        # Yeni token yarat
        token = AdminAuthToken.objects.create(user=user)

        return Response(
            {
                'token': token.token,
                'expires_at': token.expires_at,
                'user': AdminUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class AdminLogoutAPIView(APIView):
    """
    POST /api/admin/auth/logout/
    Aktiv token-i ləğv edir.
    """
    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.auth  # AdminTokenAuthentication token_obj qaytarır
        if isinstance(token, AdminAuthToken):
            token.delete()
        return Response(
            {'message': 'Uğurla çıxış edildi.'},
            status=status.HTTP_200_OK,
        )


class AdminMeAPIView(APIView):
    """
    GET /api/admin/auth/me/
    Cari daxil olmuş admin istifadəçinin məlumatlarını qaytarır.
    """
    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminPanelUser]

    def get(self, request):
        return Response(
            AdminUserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )


class AdminRefreshTokenAPIView(APIView):
    """
    POST /api/admin/auth/refresh/
    Token-in bitmə müddətini 30 gün uzadır.
    """
    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.auth
        if isinstance(token, AdminAuthToken):
            token.refresh()
            return Response(
                {
                    'token': token.token,
                    'expires_at': token.expires_at,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {'error': 'Etibarlı token tapılmadı.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
