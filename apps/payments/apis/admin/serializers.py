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

    ⚠️ Ödənilmiş sifarişlər is_deleted=True olaraq işarələnir.
    OrderManager və OrderItemManager hər ikisi is_deleted=False filtri tətbiq edir.
    Bu səbəbdən p.orders.all() və order.order_items.all() boş qaytarır.
    Həll: M2M through cədvəlindən birbaşa order_id-lər alınır,
    sonra all_orders() / all_order_items() ilə silinmiş qeydlər də daxil edilir.
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

    # ── shared helpers ────────────────────────────────────────

    def _get_context(self, obj):
        """
        Bütün 3 method üçün lazım olan datanı bir dəfə yükləyir.
        context dict-ə cache edir ki, serializer.data çağrılanda
        hər method ayrı-ayrı DB sorğusu etməsin.
        """
        from collections import defaultdict

        from apps.orders.models.order import Order, OrderItem
        from apps.payments.models.pay_table_orders import \
            Payment as PaymentModel

        cache_key = f"_calc_ctx_{obj.pk}"
        if hasattr(self, cache_key):
            return getattr(self, cache_key)

        through = PaymentModel.orders.through

        # 1. Bu hesablamaya aid bütün payment-lər (prefetch_related ilə gəlir)
        payments_qs = obj.payments.all()

        # 2. payment_id → Payment obyekti xəritəsi
        payment_map = {p.id: p for p in payments_qs}
        payment_ids = list(payment_map.keys())

        # 3. M2M through cədvəlindən (payment_id, order_id) cütlərini al
        pairs = list(
            through.objects.filter(payment_id__in=payment_ids)
            .values("payment_id", "order_id")
        )

        # payment_id → [order_id, ...] xəritəsi
        payment_to_orders = defaultdict(list)
        for pair in pairs:
            payment_to_orders[pair["payment_id"]].append(pair["order_id"])

        all_order_ids = [p["order_id"] for p in pairs]

        # 4. Silinmiş sifarişlər daxil olmaqla — all_orders() bypass edir
        orders_info = {
            o.id: {
                "waitress_id": o.waitress_id,
                "waitress_name": (
                    o.waitress.get_full_name() or o.waitress.username
                    if o.waitress else None
                ),
            }
            for o in Order.objects.all_orders()
            .filter(id__in=all_order_ids)
            .select_related("waitress")
            .only("id", "waitress__id", "waitress__first_name",
                  "waitress__last_name", "waitress__username")
        }

        # 5. OrderItem — all_order_items() bypass edir is_deleted filter
        items_qs = (
            OrderItem.objects.all_order_items()
            .filter(order_id__in=all_order_ids)
            .select_related("meal")
            .only("id", "order_id", "meal__id", "meal__name", "quantity", "price")
        )
        # order_id → [item, ...] xəritəsi
        order_to_items = defaultdict(list)
        for item in items_qs:
            order_to_items[item.order_id].append(item)

        ctx = {
            "payment_map": payment_map,
            "payment_ids": payment_ids,
            "payment_to_orders": payment_to_orders,
            "orders_info": orders_info,
            "order_to_items": order_to_items,
        }
        setattr(self, cache_key, ctx)
        return ctx

    # ── get_payments ──────────────────────────────────────────

    def get_payments(self, obj):
        from django.utils.timezone import localtime
        ctx = self._get_context(obj)

        results = []
        for p in ctx["payment_map"].values():
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
            results.append({
                "id": p.id,
                "table_number": p.table.number if p.table else None,
                "final_price": str(p.final_price),
                "paid_amount": str(p.paid_amount),
                "payment_methods": methods,
                "operator_username": p.paid_by.username if p.paid_by else None,
                "paid_at": localtime(p.paid_at).strftime("%d.%m.%Y %H:%M"),
            })
        # paid_at azalan sıra
        results.sort(key=lambda x: x["paid_at"])
        return results

    # ── get_waiter_summary ────────────────────────────────────

    def get_waiter_summary(self, obj):
        from collections import defaultdict
        from decimal import Decimal
        ctx = self._get_context(obj)

        summary = defaultdict(lambda: {
            "waiter_id": None,
            "waiter_name": "Ofisiant təyin edilməyib",
            "order_count": 0,
            "payment_count": 0,
            "total_amount": Decimal(0),
            "cash_amount": Decimal(0),
            "card_amount": Decimal(0),
            "other_amount": Decimal(0),
        })

        for payment_id, p in ctx["payment_map"].items():
            order_ids = ctx["payment_to_orders"].get(payment_id, [])

            # Ofisiantı bu ödənişin sifarişlərindən tap
            waiter_id = None
            waiter_name = "Ofisiant təyin edilməyib"
            for oid in order_ids:
                info = ctx["orders_info"].get(oid)
                if info and info["waitress_id"]:
                    waiter_id = info["waitress_id"]
                    waiter_name = info["waitress_name"] or "Ofisiant təyin edilməyib"
                    break

            bucket = summary[waiter_id]
            bucket["waiter_id"] = waiter_id
            bucket["waiter_name"] = waiter_name
            bucket["payment_count"] += 1
            bucket["order_count"] += len(order_ids)
            bucket["total_amount"] += p.final_price

            for m in p.payment_methods.all():
                if m.payment_type == "cash":
                    bucket["cash_amount"] += m.amount
                elif m.payment_type == "card":
                    bucket["card_amount"] += m.amount
                else:
                    bucket["other_amount"] += m.amount
            if not p.payment_methods.all():
                if p.payment_type == "cash":
                    bucket["cash_amount"] += p.paid_amount
                elif p.payment_type == "card":
                    bucket["card_amount"] += p.paid_amount
                elif p.payment_type:
                    bucket["other_amount"] += p.paid_amount

        return sorted(
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
            key=lambda x: float(x["total_amount"]),
            reverse=True,
        )

    # ── get_product_summary ───────────────────────────────────

    def get_product_summary(self, obj):
        from collections import defaultdict
        from decimal import Decimal
        ctx = self._get_context(obj)

        summary = defaultdict(lambda: {"meal_name": "", "quantity": 0, "total": Decimal(0)})

        for items in ctx["order_to_items"].values():
            for item in items:
                key = item.meal_id
                summary[key]["meal_name"] = item.meal.name
                summary[key]["quantity"] += item.quantity
                summary[key]["total"] += item.price

        return sorted(
            [
                {
                    "meal_name": v["meal_name"],
                    "quantity": v["quantity"],
                    "total_amount": str(round(v["total"], 2)),
                }
                for v in summary.values()
            ],
            key=lambda x: float(x["total_amount"]),
            reverse=True,
        )
