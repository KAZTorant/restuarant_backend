from datetime import date, datetime, timedelta
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.tables.models import Room, Table
from apps.tenants.models import Restaurant
from apps.users.models import User


class ActiveOrdersAPITestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create a test room first
        self.room = Room.objects.create(
            name='Test Room',
            is_active=True
        )

        # Create a test user (waitress)
        self.user = User.objects.create(
            username='test_waitress',
            password='testpass123',
            first_name='Test',
            last_name='Waitress'
        )

        # Create a test table
        self.table = Table.objects.create(
            number=1,
            capacity=4,
            room=self.room,
        )

        # Create orders with different dates
        now = timezone.now()
        yesterday = now - timedelta(days=1)

        # Today's paid order
        self.today_paid_order = Order.objects.create(
            table=self.table,
            waitress=self.user,
            is_paid=True,
            is_deleted=False,
            total_price=Decimal('50.00')
        )
        self.today_paid_order.created_at = now
        self.today_paid_order.save()

        # Today's unpaid order
        self.today_unpaid_order = Order.objects.create(
            table=self.table,
            waitress=self.user,
            is_paid=False,
            is_deleted=False,
            total_price=Decimal('30.00')
        )
        self.today_unpaid_order.created_at = now
        self.today_unpaid_order.save()

        # Yesterday's paid order
        self.yesterday_order = Order.objects.create(
            table=self.table,
            waitress=self.user,
            is_paid=True,
            is_deleted=False,
            total_price=Decimal('25.00')
        )
        self.yesterday_order.created_at = yesterday
        self.yesterday_order.save()

    def test_active_orders_no_filter(self):
        """Test API without any date filters"""
        response = self.client.get('/orders/active-orders/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should include all orders
        self.assertIn('cash_total', data)
        self.assertIn('card_total', data)
        self.assertIn('other_total', data)
        self.assertIn('unpaid_total', data)
        self.assertIn('paid_total', data)
        self.assertEqual(data['unpaid_total'], 30.0)

    def test_active_orders_date_filter(self):
        """Test API with date filter for today"""
        today = date.today().isoformat()
        response = self.client.get(f'/orders/active-orders/?date={today}')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should only include today's orders
        # Only today's unpaid order
        self.assertEqual(data['unpaid_total'], 30.0)
        self.assertIn('filters_applied', data)
        self.assertEqual(data['filters_applied']['date'], today)

    def test_active_orders_start_date_filter(self):
        """Test API with start_date filter"""
        today = timezone.now().isoformat()
        response = self.client.get(
            f'/orders/active-orders/?start_date={today}'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should include orders from today onwards
        self.assertIn('filters_applied', data)
        self.assertEqual(data['filters_applied']['start_date'], today)

    def test_active_orders_invalid_date_format(self):
        """Test API with invalid date format"""
        response = self.client.get('/orders/active-orders/?date=invalid-date')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Invalid date format', data['error'])

    def test_active_orders_invalid_start_date_format(self):
        """Test API with invalid start_date format"""
        response = self.client.get(
            '/orders/active-orders/?start_date=invalid-datetime')

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Invalid start_date format', data['error'])


class WaitressRestaurantScopeTests(TestCase):
    def setUp(self):
        self.demo = Restaurant.objects.create(name='Demo', slug='demo')
        self.other = Restaurant.objects.create(name='Other', slug='other')
        demo_room = Room.objects.create(name='Demo zal', restaurant=self.demo, is_active=True)
        self.table = Table.objects.create(number='1', room=demo_room)
        self.admin = User.objects.create(
            username='0000', type='admin', restaurant=self.demo,
            first_name='Demo', last_name='Admin',
        )
        self.own_waitress = User.objects.create(
            username='1111', type='waitress', restaurant=self.demo,
            first_name='Demo', last_name='Ofisiant',
        )
        self.other_waitress = User.objects.create(
            username='2222', type='waitress', restaurant=self.other,
            first_name='Other', last_name='Ofisiant',
        )
        self.order = Order.objects.create(
            table=self.table,
            waitress=self.own_waitress,
            is_paid=False,
            total_price=Decimal('10.00'),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_list_shows_only_current_restaurant_waitresses(self):
        response = self.client.get(
            '/api/orders/list-waitress/',
            HTTP_X_RESTAURANT_SLUG='demo',
        )

        self.assertEqual(response.status_code, 200)
        names = [row['full_name'] for row in response.json()]
        self.assertEqual(names, ['Demo Ofisiant'])

    def test_change_rejects_waitress_from_another_restaurant(self):
        response = self.client.post(
            f'/api/orders/{self.table.id}/change-waitress/',
            {'new_waitress_id': self.other_waitress.id},
            format='json',
            HTTP_X_RESTAURANT_SLUG='demo',
        )

        self.assertEqual(response.status_code, 404)
        self.order.refresh_from_db()
        self.assertEqual(self.order.waitress_id, self.own_waitress.id)

    def test_change_assigns_waitress_from_same_restaurant(self):
        replacement = User.objects.create(
            username='3333', type='waitress', restaurant=self.demo,
            first_name='Yeni', last_name='Ofisiant',
        )
        response = self.client.post(
            f'/api/orders/{self.table.id}/change-waitress/',
            {'new_waitress_id': replacement.id},
            format='json',
            HTTP_X_RESTAURANT_SLUG='demo',
        )

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.waitress_id, replacement.id)
