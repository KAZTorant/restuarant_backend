from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.translation import gettext_lazy as _
from apps.printers.utils.service_v2 import PrinterService
from apps.tables.models import Table
from apps.users.permissions import IsAdmin
from apps.payments.models import Payment, PaymentMethod

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
            200: openapi.Response(description="Ödəniş uğurla tamamlandı"),
            400: openapi.Response(description="Əlavə məlumat xətası"),
            404: openapi.Response(description="Masa tapılmadı və ya sifariş yoxdur"),
        }
    )
    def post(self, request, table_id):
        data = request.data

        # STEP 1: Check table and orders
        table, orders_or_error = self._get_validated_table_and_orders(table_id)
        if not table:
            return orders_or_error  # It's a Response object with error

        # STEP 2: Handle payment methods
        payment_methods = data.get('payment_methods', [])
        if payment_methods:
            # Validate payment methods
            total_paid = sum(Decimal(str(method['amount']))
                             for method in payment_methods)
            if total_paid != Decimal(str(data.get('paid_amount', 0))):
                return Response({
                    "success": False,
                    "message": _("Ödəniş metodlarının cəmi ödənilən məbləğə bərabər olmalıdır.")
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Use single payment type (backward compatibility)
            payment_methods = [{
                'payment_type': data.get('payment_type'),
                'amount': data.get('paid_amount')
            }]

        # STEP 3: Calculate totals
        totals, error = self._calculate_payment_details(
            orders=orders_or_error,
            discount=float(data.get('discount_amount', 0)),
            paid=float(data.get('paid_amount', 0))
        )
        if error:
            return error  # Response with error

        # STEP 4: Try printing
        self._handle_printing(
            table_id=table_id,
            is_paid=True,
            payment_type=data.get('payment_type'),
            payment_methods=payment_methods,
            discount_amount=totals['discount'],
            discount_comment=data.get('discount_comment', ''),
            paid_amount=totals['paid'],
            change=totals['change']
        )

        # STEP 5: Save payment
        payment = self._create_payment_record(
            table=table,
            orders=orders_or_error,
            totals=totals,
            user=request.user,
            payment_type=data.get('payment_type'),
            payment_methods=payment_methods,
            discount_comment=data.get('discount_comment', '')
        )

        # STEP 6: Mark as paid
        for order in orders_or_error:
            order.is_paid = True
            order.save()

        return Response(
            {
                "success": True,
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

    # ============================
    #        Helper Methods
    # ============================

    @staticmethod
    def _get_validated_table_and_orders(table_id):
        table = Table.objects.filter(id=table_id).first()
        if not table:
            return None, Response({"errors": _("Masa tapılmadı.")}, status=status.HTTP_404_NOT_FOUND)

        orders = table.orders.exclude(is_deleted=True).filter(is_paid=False)
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
