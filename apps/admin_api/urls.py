from django.urls import path

from apps.admin_api.views import (
    AuthLoginView,
    AuthLogoutView,
    AuthMeView,
    ModelActionView,
    ModelCreateView,
    ModelDetailView,
    ModelListView,
    ModelMetaView,
    NavigationView,
    RelatedChoicesView,
)
from apps.admin_api.views_custom import (
    PaymentCalculationCustomView,
    PrinterScanView,
    ShiftHandoverConfirmView,
    StatisticsCustomView,
    SummaryCustomView,
    WithdrawnListCustomView,
)

urlpatterns = [
    # Auth
    path('auth/login/', AuthLoginView.as_view(), name='admin-api-login'),
    path('auth/logout/', AuthLogoutView.as_view(), name='admin-api-logout'),
    path('auth/me/', AuthMeView.as_view(), name='admin-api-me'),

    # Navigation
    path('navigation/', NavigationView.as_view(), name='admin-api-navigation'),

    # Custom workflows
    path('custom/statistics/<str:action>/', StatisticsCustomView.as_view(), name='admin-api-statistics'),
    path('custom/summary/<str:action>/', SummaryCustomView.as_view(), name='admin-api-summary'),
    path('custom/summary/<str:action>/<int:pk>/', SummaryCustomView.as_view(), name='admin-api-summary-detail'),
    path('custom/payment-calculation/<str:action>/', PaymentCalculationCustomView.as_view(), name='admin-api-payment-calc'),
    path('custom/withdrawn-list/calculate-total/', WithdrawnListCustomView.as_view(), name='admin-api-withdrawn'),
    path('custom/printers/scan/', PrinterScanView.as_view(), name='admin-api-printer-scan'),
    path('custom/shift-handover/<int:pk>/confirm/', ShiftHandoverConfirmView.as_view(), name='admin-api-handover-confirm'),

    # Generic CRUD
    path('<str:app_label>/<str:model_name>/meta/', ModelMetaView.as_view(), name='admin-api-meta'),
    path('<str:app_label>/<str:model_name>/', ModelListView.as_view(), name='admin-api-list'),
    path('<str:app_label>/<str:model_name>/create/', ModelCreateView.as_view(), name='admin-api-create'),
    path('<str:app_label>/<str:model_name>/choices/', RelatedChoicesView.as_view(), name='admin-api-choices'),
    path('<str:app_label>/<str:model_name>/actions/<str:action_name>/', ModelActionView.as_view(), name='admin-api-action'),
    path('<str:app_label>/<str:model_name>/<int:pk>/', ModelDetailView.as_view(), name='admin-api-detail'),
]
