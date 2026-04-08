from rest_framework import serializers

from apps.orders.models.order import Order, OrderItem
from apps.payments.models import Payment, PaymentCalculation, PaymentMethod

# ─────────────────────────────────────────────
#  PAYMENT METHOD
# ─────────────────────────────────────────────

class AdminPaymentMethodSerializer(serializers.ModelSerializer):
    payment_type_display = serializers.CharField(
        source="get_payment_type_display", read_only=True
    )

    class Meta:
        model = PaymentMethod
        fields = ("id", "payment_type", "payment_type_display", "amount")


# ─────────────────────────────────────────────
#  PAYMENT (Ödəmə) — Read-only
# ─────────────────────────────────────────────

class AdminPaymentListSerializer(serializers.ModelSerializer):
    """Siyahı üçün yüngül serializer — N+1 yoxdur"""
    table_number = serializers.CharField(source="table.number", read_only=True)
    room_name = serializers.CharField(source="table.room.name", read_only=True)
    paid_by_name = serializers.CharField(source="paid_by.get_full_name", read_only=True)
    paid_by_username = serializers.CharField(source="paid_by.username", read_only=True)
    payment_methods = AdminPaymentMethodSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "table",
            "table_number",
            "room_name",
            "total_price",
            "discount_amount",
            "discount_comment",
            "final_price",
            "paid_amount",
            "change",
            "payment_type",
            "payment_methods",
            "paid_by",
            "paid_by_name",
            "paid_by_username",
            "paid_at",
        )


class AdminPaymentDetailSerializer(AdminPaymentListSerializer):
    """Detal üçün — əlaqəli sifarişlər məhsulları ilə birlikdə"""
    orders = serializers.SerializerMethodField()

    class Meta(AdminPaymentListSerializer.Meta):
        fields = AdminPaymentListSerializer.Meta.fields + ("orders",)

    def get_orders(self, obj):
        results = []
        for order in obj.orders.all():
            items = []
            for item in order.order_items.select_related("meal").all():
                unit_price = (
                    item.price / item.quantity
                    if item.quantity > 0 else item.price
                )
                items.append({
                    "id": item.id,
                    "meal_id": item.meal_id,
                    "meal_name": item.meal.name,
                    "quantity": item.quantity,
                    "unit_price": str(round(unit_price, 2)),
                    "total_price": str(item.price),
                    "comment": item.comment,
                })
            results.append({
                "id": order.id,
                "total_price": str(order.total_price),
                "waitress_id": order.waitress_id,
                "waitress_name": (
                    order.waitress.get_full_name() or order.waitress.username
                    if order.waitress else None
                ),
                "items": items,
            })
        return results


# ─────────────────────────────────────────────
#  PAYMENT CALCULATION (Ödəniş hesablaması)
# ─────────────────────────────────────────────

class AdminPaymentCalculationListSerializer(serializers.ModelSerializer):
    """Siyahı üçün yüngül serializer"""
    date_range_display = serializers.CharField(read_only=True)
    time_range_display = serializers.CharField(read_only=True)
    extra_paid_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True
    )
    total_paid = serializers.SerializerMethodField()

    class Meta:
        model = PaymentCalculation
        fields = (
            "id",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "date_range_display",
            "time_range_display",
            "total_amount",
            "total_paid",
            "payment_count",
            "cash_amount",
            "card_amount",
            "other_amount",
            "extra_paid_amount",
            "created_by",
            "created_by_username",
            "created_at",
        )

    def get_total_paid(self, obj):
        return obj.cash_amount + obj.card_amount + obj.other_amount


class AdminPaymentCalculationCreateSerializer(serializers.Serializer):
    """Yeni hesablama yaratmaq üçün input serializer"""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    start_time = serializers.TimeField(default="12:00")
    end_time = serializers.TimeField(default="23:59")

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "Son tarix başlanğıc tarixdən əvvəl ola bilməz."}
            )
        if (
            attrs["start_date"] == attrs["end_date"]
            and attrs["start_time"] >= attrs["end_time"]
        ):
            raise serializers.ValidationError(
                {"end_time": "Son saat başlanğıc saatdan əvvəl ola bilməz."}
            )
        return attrs


class AdminPaymentCalculationDetailSerializer(AdminPaymentCalculationListSerializer):
    """
    Detal — 3 əlavə blok:
      • payments        → ödənişlərin tam siyahısı (masa, məbləğ, növ, operator, tarix)
      • waiter_summary  → ofisiant üzrə xülasə
      • product_summary → satılan məhsullar xülasəsi
    """
    payments = serializers.SerializerMethodField()
    waiter_summary = serializers.SerializerMethodField()
    product_summary = serializers.SerializerMethodField()

    class Meta(AdminPaymentCalculationListSerializer.Meta):
        fields = AdminPaymentCalculationListSerializer.Meta.fields + (
            "payments",
            "waiter_summary",
            "product_summary",
        )

    def get_payments(self, obj):
        results = []
        for p in obj.payments.all():
            methods = [
                {
                    "payment_type": m.payment_type,
                    "payment_type_display": m.get_payment_type_display(),
                    "amount": str(m.amount),
                }
                for m in p.payment_methods.all()
            ]
            if not methods and p.payment_type:
                methods = [{
                    "payment_type": p.payment_type,
                    "payment_type_display": p.get_payment_type_display(),
                    "amount": str(p.paid_amount),
                }]
            from django.utils.timezone import localtime
            results.append({
                "id": p.id,
                "table_number": p.table.number if p.table else None,
                "final_price": str(p.final_price),
                "paid_amount": str(p.paid_amount),
                "payment_methods": methods,
                "operator_username": p.paid_by.username if p.paid_by else None,
                "paid_at": localtime(p.paid_at).strftime("%d.%m.%Y %H:%M"),
            })
        return results

    def get_waiter_summary(self, obj):
        from collections import defaultdict
        from decimal import Decimal

        summary = defaultdict(lambda: {
            "waiter_id": None,
            "waiter_name": "",
            "order_count": 0,
            "payment_count": 0,
            "total_amount": Decimal(0),
            "cash_amount": Decimal(0),
            "card_amount": Decimal(0),
            "other_amount": Decimal(0),
        })

        for p in obj.payments.all():
            # Ofisiantları tap
            waiters = set()
            for order in p.orders.all():
                if order.waitress_id:
                    name = (
                        order.waitress.get_full_name()
                        or order.waitress.username
                    )
                    waiters.add((order.waitress_id, name))

            key = list(waiters)[0] if waiters else (None, "Ofisiant təyin edilməyib")
            waiter_id, waiter_name = key

            bucket = summary[waiter_id]
            bucket["waiter_id"] = waiter_id
            bucket["waiter_name"] = waiter_name
            bucket["payment_count"] += 1
            bucket["order_count"] += p.orders.count()
            bucket["total_amount"] += p.final_price

            if p.payment_methods.all():
                for m in p.payment_methods.all():
                    if m.payment_type == "cash":
                        bucket["cash_amount"] += m.amount
                    elif m.payment_type == "card":
                        bucket["card_amount"] += m.amount
                    else:
                        bucket["other_amount"] += m.amount
            else:
                if p.payment_type == "cash":
                    bucket["cash_amount"] += p.paid_amount
                elif p.payment_type == "card":
                    bucket["card_amount"] += p.paid_amount
                else:
                    bucket["other_amount"] += p.paid_amount

        rows = sorted(
            [
                {
                    "waiter_id": v["waiter_id"],
                    "waiter_name": v["waiter_name"],
                    "order_count": v["order_count"],
                    "payment_count": v["payment_count"],
                    "total_amount": str(round(v["total_amount"], 2)),
                    "cash_amount": str(round(v["cash_amount"], 2)),
                    "card_amount": str(round(v["card_amount"], 2)),
                    "other_amount": str(round(v["other_amount"], 2)),
                }
                for v in summary.values()
            ],
            key=lambda x: x["total_amount"],
            reverse=True,
        )
        return rows

    def get_product_summary(self, obj):
        from collections import defaultdict

        summary = defaultdict(lambda: {"quantity": 0, "total": 0.0})

        for p in obj.payments.all():
            for order in p.orders.all():
                for item in order.order_items.all():
                    summary[item.meal.name]["quantity"] += item.quantity
                    summary[item.meal.name]["total"] += float(item.price)

        return sorted(
            [
                {
                    "meal_name": name,
                    "quantity": data["quantity"],
                    "total_amount": str(round(data["total"], 2)),
                }
                for name, data in summary.items()
            ],
            key=lambda x: x["total_amount"],
            reverse=True,
        )

    # köhnə fields blokunun tərifi
    class Meta(AdminPaymentCalculationListSerializer.Meta):
        fields = AdminPaymentCalculationListSerializer.Meta.fields + (
            "payments",
            "waiter_summary",
            "product_summary",
        )

    def get_payment_ids(self, obj):
        return list(obj.payments.values_list("id", flat=True))
