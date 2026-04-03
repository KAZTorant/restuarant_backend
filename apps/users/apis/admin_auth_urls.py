from django.urls import path

from apps.users.apis.admin_auth import (AdminLoginAPIView, AdminLogoutAPIView,
                                        AdminMeAPIView,
                                        AdminRefreshTokenAPIView)

urlpatterns = [
    path('login/', AdminLoginAPIView.as_view(), name='admin-login'),
    path('logout/', AdminLogoutAPIView.as_view(), name='admin-logout'),
    path('me/', AdminMeAPIView.as_view(), name='admin-me'),
    path('refresh/', AdminRefreshTokenAPIView.as_view(), name='admin-token-refresh'),
]
