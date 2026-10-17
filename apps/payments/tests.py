from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.test import TestCase
from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.payments.admin.payment import PaymentAdmin
from apps.payments.models import PartialPayment, Payment, PaymentMethod
from apps.tables.models import Room, Table
from apps.tenants.models import Restaurant
from apps.users.models import User


class PartialTablePaymentTests(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(name='Kazza', slug='kazza')
        self.room = Room.objects.create(
            name='Zal', restaurant=self.restaurant, is_active=True,
        )
        self.table = Table.objects.create(number='5', capacity=4, room=self.room)
        self.admin = User.objects.create(
            username='1111', type='admin', restaurant=self.restaurant,
        )
        self.order = Order.objects.create(
            table=self.table,
            waitress=self.admin,
            is_paid=False,
            is_main=True,
            total_price=Decimal('14.00'),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        self.url = f'/api/payments/{self.table.id}/pay-orders/'

    def _pay(self, amount, payment_type='cash', discount=0):
        return self.client.post(self.url, {
            'payment_methods': [{'payment_type': payment_type, 'amount': amount}],
            'paid_amount': amount,
            'discount_amount': discount,
            'discount_comment': '',
        }, format='json')

    @patch('apps.payments.apis.pay_table_orders.PrinterService.print_orders_for_table')
    def test_partial_payment_keeps_bill_open_and_shows_remainder(self, print_mock):
        response = self._pay(5)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['partial'])
        self.assertEqual(response.data['details']['paid_amount'], 5)
        self.assertEqual(response.data['details']['remaining'], 9)
        self.assertEqual(len(response.data['details']['payments']), 1)
        self.assertEqual(response.data['details']['payments'][0]['amount'], 5)
        self.assertIsNotNone(response.data['details']['payments'][0]['paid_at'])

        self.order.refresh_from_db()
        self.assertFalse(self.order.is_paid)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(PartialPayment.objects.filter(payment__isnull=True).count(), 1)
        print_mock.assert_not_called()

        status_response = self.client.get(self.url)
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data['paid_amount'], 5)
        self.assertEqual(status_response.data['remaining'], 9)

    @patch('apps.payments.apis.pay_table_orders.PrinterService.print_orders_for_table')
    def test_bill_becomes_one_payment_only_after_it_is_fully_paid(self, print_mock):
        self._pay(5, 'cash')
        response = self._pay(9, 'card')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['partial'])
        self.assertEqual(Payment.objects.count(), 1)

        payment = Payment.objects.get()
        self.assertEqual(payment.final_price, Decimal('14.00'))
        self.assertEqual(payment.paid_amount, Decimal('14.00'))
        self.assertEqual(payment.change, Decimal('0.00'))
        self.assertEqual(payment.partial_payments.count(), 2)
        self.assertEqual(
            list(payment.partial_payments.order_by('id').values_list('amount', 'payment_type')),
            [(Decimal('5.00'), 'cash'), (Decimal('9.00'), 'card')],
        )
        self.assertEqual(PaymentMethod.objects.filter(payment=payment).count(), 2)
        self.assertEqual(
            sum(method.amount for method in payment.payment_methods.all()),
            Decimal('14.00'),
        )

        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        self.assertEqual(PartialPayment.objects.filter(payment__isnull=True).count(), 0)
        print_mock.assert_called_once()

        history = str(PaymentAdmin(Payment, admin.site).installments_display(payment))
        self.assertIn('Nağd 5.00₼', history)
        self.assertIn('Kart 9.00₼', history)
        self.assertIn('<br>', history)

        status_response = self.client.get(self.url)
        self.assertEqual(status_response.data['paid_amount'], 0)
        self.assertEqual(status_response.data['payments'], [])

    @patch('apps.payments.apis.pay_table_orders.PrinterService.print_orders_for_table')
    def test_full_payment_still_creates_a_single_payment_without_partials(self, print_mock):
        response = self._pay(14)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['partial'])
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(PartialPayment.objects.count(), 0)

        payment = Payment.objects.get()
        self.assertEqual(payment.paid_amount, Decimal('14.00'))
        self.assertEqual(payment.final_price, Decimal('14.00'))
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        print_mock.assert_called_once()
