from django.urls import path

from apps.payments.apis.admin.views import (
    AdminPaymentCalculationListCreateAPIView,
    AdminPaymentCalculationRetrieveDestroyAPIView, AdminPaymentListAPIView,
    AdminPaymentRetrieveAPIView)

urlpatterns = [
    # ── Payments (Ödəmələr) ── read-only ─────────────────────
    path(
        "payments/",
        AdminPaymentListAPIView.as_view(),
        name="admin-payment-list",
    ),
    path(
        "payments/<int:pk>/",
        AdminPaymentRetrieveAPIView.as_view(),
        name="admin-payment-detail",
    ),

    # ── Payment Calculations (Ödəniş hesablamaları) ──────────
    path(
        "calculations/",
        AdminPaymentCalculationListCreateAPIView.as_view(),
        name="admin-payment-calculation-list-create",
    ),
    path(
        "calculations/<int:pk>/",
        AdminPaymentCalculationRetrieveDestroyAPIView.as_view(),
        name="admin-payment-calculation-detail",
    ),
]
