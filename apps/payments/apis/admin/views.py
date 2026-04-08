from datetime import datetime

from django.db.models import Prefetch, Q
from django.utils import timezone
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models.order import Order, OrderItem
from apps.payments.apis.admin.serializers import (
    AdminPaymentCalculationCreateSerializer,
    AdminPaymentCalculationDetailSerializer,
    AdminPaymentCalculationListSerializer, AdminPaymentDetailSerializer,
    AdminPaymentListSerializer)
from apps.payments.models import Payment, PaymentCalculation, PaymentMethod
from apps.users.permissions import IsAdminPanelUser


class AdminRequiredMixin:
    permission_classes = [IsAdminPanelUser]


# ─────────────────────────────────────────────
#  PAYMENT (Ödəmə) — Read-only
# ─────────────────────────────────────────────

class AdminPaymentListAPIView(AdminRequiredMixin, generics.ListAPIView):
    """
    GET → Ödəmələrin siyahısı
    Filter: payment_type, paid_by, table_id, start_date, end_date
    """
    serializer_class = AdminPaymentListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["table__number", "table__room__name", "paid_by__username"]
    ordering_fields = ["id", "final_price", "paid_at"]
    ordering = ["-paid_at"]

    def get_queryset(self):
        qs = (
            Payment.objects
            .select_related("table__room", "paid_by")
            .prefetch_related(
                Prefetch(
                    "payment_methods",
                    queryset=PaymentMethod.objects.only(
                        "id", "payment_id", "payment_type", "amount"
                    ),
                )
            )
        )

        params = self.request.query_params

        # Filter: ödəniş növü
        payment_type = params.get("payment_type")
        if payment_type:
            qs = qs.filter(payment_type=payment_type)

        # Filter: operator
        paid_by = params.get("paid_by")
        if paid_by:
            qs = qs.filter(paid_by__id=paid_by)

        # Filter: masa
        table_id = params.get("table_id")
        if table_id:
            qs = qs.filter(table__id=table_id)

        # Filter: tarix aralığı
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        if start_date:
            qs = qs.filter(paid_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(paid_at__date__lte=end_date)

        return qs


class AdminPaymentRetrieveAPIView(AdminRequiredMixin, generics.RetrieveAPIView):
    """
    GET → Ödəmə detalları (əlaqəli sifariş ID-ləri daxil)
    """
    serializer_class = AdminPaymentDetailSerializer

    def get_queryset(self):
        return (
            Payment.objects
            .select_related("table__room", "paid_by")
            .prefetch_related(
                Prefetch(
                    "payment_methods",
                    queryset=PaymentMethod.objects.only(
                        "id", "payment_id", "payment_type", "amount"
                    ),
                ),
                Prefetch(
                    "orders",
                    queryset=Order.objects.all_orders().prefetch_related(
                        Prefetch(
                            "order_items",
                            queryset=OrderItem.objects.select_related("meal").only(
                                "id", "order_id", "meal__id", "meal__name",
                                "quantity", "price", "comment",
                            ),
                        )
                    ).select_related("waitress").only(
                        "id", "total_price", "waitress__id",
                        "waitress__first_name", "waitress__last_name",
                        "waitress__username",
                    ),
                ),
            )
        )


# ─────────────────────────────────────────────
#  PAYMENT CALCULATION (Ödəniş hesablaması)
# ─────────────────────────────────────────────

class AdminPaymentCalculationListCreateAPIView(AdminRequiredMixin, APIView):
    """
    GET  → Hesablamaların siyahısı (pagination + filter)
    POST → Yeni hesablama yarat (tarix/saat aralığına görə)
    """

    def get(self, request):
        qs = (
            PaymentCalculation.objects
            .select_related("created_by")
            .only(
                "id", "start_date", "end_date", "start_time", "end_time",
                "total_amount", "payment_count", "cash_amount", "card_amount",
                "other_amount", "created_by__username", "created_at",
            )
            .order_by("-created_at")
        )

        # Filter: yaradan
        created_by = request.query_params.get("created_by")
        if created_by:
            qs = qs.filter(created_by__id=created_by)

        # Filter: tarix aralığı (yaradılma tarixi)
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            qs = qs.filter(start_date__gte=start_date)
        if end_date:
            qs = qs.filter(end_date__lte=end_date)

        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminPaymentCalculationListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = AdminPaymentCalculationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        start_dt = datetime.combine(data["start_date"], data["start_time"])
        end_dt = datetime.combine(data["end_date"], data["end_time"])

        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt)
        if timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(end_dt)

        # Ödənişləri çək — payment_methods da birlikdə
        payments = (
            Payment.objects
            .filter(paid_at__gte=start_dt, paid_at__lte=end_dt)
            .prefetch_related("payment_methods")
        )

        total_amount = sum(p.final_price for p in payments)
        payment_count = len(payments)
        cash_amount = 0
        card_amount = 0
        other_amount = 0

        for payment in payments:
            if payment.payment_methods.all():
                for method in payment.payment_methods.all():
                    if method.payment_type == "cash":
                        cash_amount += method.amount
                    elif method.payment_type == "card":
                        card_amount += method.amount
                    else:
                        other_amount += method.amount
            else:
                if payment.payment_type == "cash":
                    cash_amount += payment.paid_amount
                elif payment.payment_type == "card":
                    card_amount += payment.paid_amount
                else:
                    other_amount += payment.paid_amount

        calculation = PaymentCalculation.objects.create(
            start_date=data["start_date"],
            end_date=data["end_date"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            total_amount=total_amount,
            payment_count=payment_count,
            cash_amount=cash_amount,
            card_amount=card_amount,
            other_amount=other_amount,
            created_by=request.user,
        )
        calculation.payments.set(payments)

        out = AdminPaymentCalculationListSerializer(calculation)
        return Response(out.data, status=status.HTTP_201_CREATED)


class AdminPaymentCalculationRetrieveDestroyAPIView(AdminRequiredMixin, APIView):
    """
    GET    → Hesablama detalları (ödəniş ID siyahısı daxil)
    DELETE → Hesablamanı sil (yalnız superuser)
    """

    def _get_object(self, pk):
        try:
            return (
                PaymentCalculation.objects
                .select_related("created_by")
                .prefetch_related(
                    Prefetch(
                        "payments",
                        queryset=Payment.objects
                        .select_related("table", "paid_by")
                        .prefetch_related(
                            Prefetch(
                                "payment_methods",
                                queryset=PaymentMethod.objects.only(
                                    "id", "payment_id", "payment_type", "amount"
                                ),
                            ),
                            Prefetch(
                                "orders",
                                queryset=Order.objects.all_orders()
                                .select_related("waitress")
                                .prefetch_related(
                                    Prefetch(
                                        "order_items",
                                        queryset=OrderItem.objects.select_related("meal").only(
                                            "id", "order_id", "meal__id",
                                            "meal__name", "quantity", "price",
                                        ),
                                    )
                                )
                                .only(
                                    "id", "total_price", "waitress__id",
                                    "waitress__first_name", "waitress__last_name",
                                    "waitress__username",
                                ),
                            ),
                        ),
                    )
                )
                .get(pk=pk)
            )
        except PaymentCalculation.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_object(pk)
        if not obj:
            return Response(
                {"detail": "Hesablama tapılmadı."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = AdminPaymentCalculationDetailSerializer(obj)
        return Response(serializer.data)

    def delete(self, request, pk):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Yalnız superuser hesablamanı silə bilər."},
                status=status.HTTP_403_FORBIDDEN,
            )
        obj = self._get_object(pk)
        if not obj:
            return Response(
                {"detail": "Hesablama tapılmadı."},
                status=status.HTTP_404_NOT_FOUND,
            )
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
