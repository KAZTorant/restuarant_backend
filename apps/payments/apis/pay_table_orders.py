from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.printers.utils.service_v2 import PrinterService
from apps.tables.models import Table
from apps.users.permissions import IsAdmin
from apps.payments.models import PartialPayment, Payment, PaymentMethod

from decimal import Decimal

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class CompleteTablePaymentAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_summary="Masaya aid sifarişin ödənişini tamamla",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["payment_type", "paid_amount"],
            properties={
                "payment_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Ödəniş növü (cash, card, other)",
                    enum=["cash", "card", "other"]
                ),
                "payment_methods": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="Multiple payment methods (optional)",
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        required=["payment_type", "amount"],
                        properties={
                            "payment_type": openapi.Schema(
                                type=openapi.TYPE_STRING,
                                description="Ödəniş növü (cash, card, other)",
                                enum=["cash", "card", "other"]
                            ),
                            "amount": openapi.Schema(
                                type=openapi.TYPE_NUMBER,
                                description="Bu ödəniş növü üçün məbləğ (₼)"
                            )
                        }
                    )
                ),
                "discount_amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description="Endirim miqdarı (₼)",
                    default=0
                ),
                "discount_comment": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Endirim səbəbi və ya qeydi",
                    default=""
                ),
                "paid_amount": openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description="Müştərinin ödədiyi məbləğ (₼)"
                )
            }
        ),
        responses={
            200: openapi.Response(description="Ödəniş uğurla tamamlandı və ya qismən qeydə alındı"),
            400: openapi.Response(description="Əlavə məlumat xətası"),
            404: openapi.Response(description="Masa tapılmadı və ya sifariş yoxdur"),
        }
    )
    def get(self, request, table_id):
        table, orders_or_error = self._get_validated_table_and_orders(table_id)
        if not table:
            if getattr(orders_or_error, 'status_code', None) == status.HTTP_404_NOT_FOUND:
                return orders_or_error
            return Response(self._empty_status(), status=status.HTTP_200_OK)

        partials = list(self._open_partials(orders_or_error))
        total = self._orders_total(orders_or_error)
        discount = partials[-1].discount_amount if partials else Decimal('0.00')
        comment = partials[-1].discount_comment if partials else ''
        final = max(total - discount, Decimal('0.00'))
        paid = self._sum_amounts(partials)
        return Response(
            self._status_payload(total, discount, comment, final, paid, partials),
            status=status.HTTP_200_OK,
        )

    def post(self, request, table_id):
        with transaction.atomic():
            return self._post_payment(request, table_id)

    def _post_payment(self, request, table_id):
        data = request.data

        # STEP 1: Check table and orders
        table, orders_or_error = self._get_validated_table_and_orders(table_id, lock=True)
        if not table:
            return orders_or_error  # It's a Response object with error

        orders = list(orders_or_error)
        this_paid = self._money(data.get('paid_amount', 0))
        discount = self._money(data.get('discount_amount', 0))
        discount_comment = data.get('discount_comment', '') or ''
        total = self._orders_total(orders)
        final = max(total - discount, Decimal('0.00'))

        # STEP 2: Handle payment methods
        payment_methods, error = self._normalize_payment_methods(data, this_paid)
        if error:
            return error

        prior = list(self._open_partials(orders))
        prior_paid = self._sum_amounts(prior)

        # Tam ödəniş, əvvəl qismən ödəniş yoxdur: köhnə axın olduğu kimi qalır.
        if prior_paid == 0 and this_paid >= final:
            totals, calc_error = self._calculate_payment_details(
                orders=orders,
                discount=float(discount),
                paid=float(this_paid),
            )
            if calc_error:
                return calc_error

            self._handle_printing(
                table_id=table_id,
                is_paid=True,
                payment_type=data.get('payment_type'),
                payment_methods=payment_methods,
                discount_amount=totals['discount'],
                discount_comment=discount_comment,
                paid_amount=totals['paid'],
                change=totals['change'],
            )
            payment = self._create_payment_record(
                table=table,
                orders=orders,
                totals=totals,
                user=request.user,
                payment_type=data.get('payment_type'),
                payment_methods=payment_methods,
                discount_comment=discount_comment,
            )
            self._mark_orders_paid(orders)
            return self._completed_response(payment, totals)

        if this_paid < 0:
            return Response({
                "success": False,
                "message": _("Ödəniş məbləği mənfi ola bilməz."),
            }, status=status.HTTP_400_BAD_REQUEST)

        if this_paid == 0 and prior_paid < final:
            return Response({
                "success": False,
                "message": _("Zəhmət olmasa ödəniş məbləğini daxil edin."),
            }, status=status.HTTP_400_BAD_REQUEST)

        if this_paid > 0:
            self._record_partials(
                table=table,
                orders=orders,
                payment_methods=payment_methods,
                user=request.user,
                discount=discount,
                discount_comment=discount_comment,
            )

        partials = list(self._open_partials(orders))
        paid = self._sum_amounts(partials)
        if paid < final:
            return Response({
                "success": True,
                "partial": True,
                "message": _("Qismən ödəniş qeydə alındı."),
                "details": self._status_payload(
                    total, discount, discount_comment, final, paid, partials,
                ),
            }, status=status.HTTP_200_OK)

        method_rows = [
            {'payment_type': item.payment_type, 'amount': item.amount}
            for item in partials
        ]
        change = paid - final
        single_type = method_rows[0]['payment_type'] if len({row['payment_type'] for row in method_rows}) == 1 else data.get('payment_type')
        totals = {
            'total': total,
            'discount': discount,
            'final': final,
            'paid': paid,
            'change': change,
        }
        self._handle_printing(
            table_id=table_id,
            is_paid=True,
            payment_type=single_type,
            payment_methods=method_rows,
            discount_amount=discount,
            discount_comment=discount_comment,
            paid_amount=paid,
            change=change,
        )
        payment = self._create_payment_record(
            table=table,
            orders=orders,
            totals=totals,
            user=request.user,
            payment_type=single_type,
            payment_methods=method_rows,
            discount_comment=discount_comment,
        )
        PartialPayment.objects.filter(pk__in=[item.pk for item in partials]).update(payment=payment)
        self._mark_orders_paid(orders)
        return self._completed_response(payment, totals)

    # ============================
    #        Helper Methods
    # ============================

    @staticmethod
    def _money(value):
        return Decimal(str(value or 0)).quantize(Decimal('0.01'))

    @staticmethod
    def _orders_total(orders):
        return sum((order.total_price for order in orders), Decimal('0.00'))

    @staticmethod
    def _sum_amounts(partials):
        return sum((item.amount for item in partials), Decimal('0.00'))

    @staticmethod
    def _open_partials(orders):
        return PartialPayment.objects.filter(
            payment__isnull=True,
            orders__in=orders,
        ).distinct().order_by('paid_at', 'id')

    @staticmethod
    def _empty_status():
        return {
            "total": 0,
            "discount": 0,
            "discount_comment": "",
            "final_price": 0,
            "paid_amount": 0,
            "remaining": 0,
            "payments": [],
        }

    @classmethod
    def _status_payload(cls, total, discount, comment, final, paid, partials):
        remaining = max(final - paid, Decimal('0.00'))
        return {
            "total": float(total),
            "discount": float(discount),
            "discount_comment": comment or "",
            "final_price": float(final),
            "paid_amount": float(paid),
            "remaining": float(remaining),
            "payments": [cls._partial_payload(item) for item in partials],
        }

    @staticmethod
    def _partial_payload(item):
        paid_at = timezone.localtime(item.paid_at) if item.paid_at else None
        return {
            "id": item.id,
            "amount": float(item.amount),
            "payment_type": item.payment_type,
            "payment_type_display": str(item.get_payment_type_display()),
            "paid_at": paid_at.isoformat() if paid_at else None,
        }

    @classmethod
    def _normalize_payment_methods(cls, data, this_paid):
        payment_methods = data.get('payment_methods', [])
        if this_paid == 0 and not payment_methods:
            return [], None
        if payment_methods:
            total_paid = sum(
                (cls._money(method['amount']) for method in payment_methods),
                Decimal('0.00'),
            )
            if total_paid != this_paid:
                return None, Response({
                    "success": False,
                    "message": _("Ödəniş metodlarının cəmi ödənilən məbləğə bərabər olmalıdır.")
                }, status=status.HTTP_400_BAD_REQUEST)
            return [
                {
                    'payment_type': method['payment_type'],
                    'amount': cls._money(method['amount']),
                }
                for method in payment_methods
                if cls._money(method['amount']) > 0
            ], None

        return [{
            'payment_type': data.get('payment_type'),
            'amount': this_paid,
        }], None

    @staticmethod
    def _record_partials(table, orders, payment_methods, user, discount, discount_comment):
        created = []
        order_list = list(orders)
        for method in payment_methods:
            partial = PartialPayment.objects.create(
                table=table,
                amount=method['amount'],
                payment_type=method['payment_type'],
                discount_amount=discount,
                discount_comment=discount_comment,
                paid_by=user,
            )
            partial.orders.set(order_list)
            created.append(partial)
        return created

    @staticmethod
    def _mark_orders_paid(orders):
        for order in orders:
            order.is_paid = True
            order.save()

    @staticmethod
    def _completed_response(payment, totals):
        return Response(
            {
                "success": True,
                "partial": False,
                "message": _("Ödəniş uğurla tamamlandı."),
                "details": {
                    "payment_id": payment.id,
                    "total_price": totals['total'],
                    "discount": totals['discount'],
                    "final_price": totals['final'],
                    "paid_amount": totals['paid'],
                    "change": totals['change'],
                    "payment_methods": [
                        {
                            "type": method.payment_type,
                            "amount": float(method.amount)
                        }
                        for method in payment.payment_methods.all()
                    ]
                }
            },
            status=status.HTTP_200_OK
        )

    @staticmethod
    def _get_validated_table_and_orders(table_id, lock=False):
        table_qs = Table.objects.filter(id=table_id)
        if lock:
            table_qs = table_qs.select_for_update()
        table = table_qs.first()
        if not table:
            return None, Response({"errors": _("Masa tapılmadı.")}, status=status.HTTP_404_NOT_FOUND)

        orders = table.orders.exclude(is_deleted=True).filter(is_paid=False)
        if lock:
            orders = orders.select_for_update()
        if not orders.exists():
            return None, Response({"success": False, "message": _("Masada sifariş yoxdur.")}, status=status.HTTP_400_BAD_REQUEST)

        return table, orders

    @staticmethod
    def _handle_printing(table_id, is_paid, payment_type, payment_methods, discount_amount, discount_comment, paid_amount, change):
        try:
            PrinterService.print_orders_for_table(
                table_id=table_id,
                is_paid=is_paid,
                force_print=True,
                payment_type=payment_type,
                payment_methods=payment_methods,
                discount_amount=discount_amount,
                discount_comment=discount_comment,
                paid_amount=paid_amount,
                change=change,
            )
        except Exception as e:
            print("Printer error:", str(e))

    @staticmethod
    def _create_payment_record(table, orders, totals, user, payment_type, payment_methods, discount_comment):
        payment = Payment.objects.create(
            table=table,
            total_price=totals['total'],
            discount_amount=totals['discount'],
            discount_comment=discount_comment,
            final_price=totals['final'],
            paid_amount=totals['paid'],
            change=totals['change'],
            payment_type=payment_type,
            paid_by=user
        )
        payment.orders.set(orders)

        # Create payment methods
        for method_data in payment_methods:
            PaymentMethod.objects.create(
                payment=payment,
                amount=Decimal(str(method_data['amount'])),
                payment_type=method_data['payment_type']
            )

        payment.save()
        return payment

    @staticmethod
    def _calculate_payment_details(orders, discount, paid):
        total = sum(order.total_price for order in orders)
        discount = Decimal(str(discount))
        paid = Decimal(str(paid))

        final = max(total - discount, Decimal("0"))

        if paid < final:
            return None, Response({
                "success": False,
                "message": _(
                    "Müştərinin ödədiyi məbləğ ({paid}₼) kifayət etmir. Ümumi məbləğ {total}₼."
                ).format(paid=paid, total=final)
            }, status=status.HTTP_400_BAD_REQUEST)

        return {
            "total": total,
            "discount": discount,
            "final": final,
            "paid": paid,
            "change": paid - final
        }, None
