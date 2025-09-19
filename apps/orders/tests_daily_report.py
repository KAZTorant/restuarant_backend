"""
Django Test Suite for Daily Report Feature ("Günün Hesabatı")

This test file covers:
1. Statistics System - How shifts work
2. Daily Report API - Payment calculations since last closed report  
3. Telegram Bot Integration - Menu and callback handling
4. Edge Cases - No closed reports, empty data, etc.

Run with: python manage.py test apps.orders.tests_daily_report
"""
import json
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.orders.models import Order, Statistics
from apps.orders.api_views import daily_report_api
from apps.payments.models import Payment, PaymentMethod
from apps.tables.models import Table

User = get_user_model()


class DailyReportTestCase(TestCase):
    """Django TestCase for Daily Report functionality"""

    def setUp(self):
        """Setup test data before each test"""
        self.client = Client()

        # Create test user and table
        self.test_user = User.objects.create_user(
            'test_daily_user',
            'test@daily.com',
            'password123'
        )
        self.test_table = Table.objects.create(number='TEST99', capacity=4)

    def tearDown(self):
        """Clean up after each test"""
        # Django automatically handles database cleanup between tests
        pass

    def create_closed_statistics_report(self, hours_ago=2):
        """Create a closed statistics report"""
        end_time = timezone.now() - timedelta(hours=hours_ago)
        start_time = end_time - timedelta(hours=8)

        closed_report = Statistics.objects.create(
            title='till_now',
            started_by=self.test_user,
            start_time=start_time,
            end_time=end_time,
            is_closed=True,
            is_z_checked=True,
            ended_by=self.test_user,
            cash_total=Decimal('100.00'),
            card_total=Decimal('200.00'),
            other_total=Decimal('50.00'),
            initial_cash=Decimal('50.00'),
            withdrawn_amount=Decimal('30.00'),
            remaining_cash=Decimal('120.00')
        )

        return closed_report

    def create_orders_after_report(self, closed_report, test_data):
        """Create orders after a closed report with payments"""
        after_time = closed_report.end_time + timedelta(minutes=30)
        created_orders = []

        for i, (price, is_paid, payment_type) in enumerate(test_data):
            # Create order
            order = Order.objects.create(
                table=self.test_table,
                waitress=self.test_user,
                total_price=price,
                is_paid=is_paid,
                created_at=after_time + timedelta(minutes=i*10)
            )
            created_orders.append(order)

            # Create payment if paid
            if is_paid and payment_type:
                payment = Payment.objects.create(
                    table=self.test_table,
                    total_price=price,
                    final_price=price,
                    paid_amount=price,
                    payment_type=payment_type.lower(),
                    paid_by=self.test_user
                )
                payment.orders.add(order)

                # Create PaymentMethod (this is what the API actually reads)
                PaymentMethod.objects.create(
                    payment=payment,
                    amount=price,
                    payment_type=payment_type.lower()
                )

        return created_orders

    def test_statistics_system(self):
        """Test 1: Verify statistics system works correctly"""
        print("\n🧪 TEST 1: Statistics System")

        # Test shift creation
        open_shift = Statistics.objects.create(
            title='till_now',
            started_by=self.test_user,
            start_time=timezone.now() - timedelta(hours=2),
            is_closed=False
        )

        # Test closing shift
        open_shift.end_time = timezone.now()
        open_shift.is_closed = True
        open_shift.ended_by = self.test_user
        open_shift.save()

        # Test finding last closed report
        last_closed = Statistics.objects.filter(
            is_closed=True).order_by('-end_time').first()
        self.assertEqual(last_closed, open_shift)

        print("✅ Statistics system working correctly")

    def test_api_no_closed_reports(self):
        """Test 2: API behavior when no closed reports exist"""
        print("\n🧪 TEST 2: API - No Closed Reports")

        # Ensure no closed reports
        Statistics.objects.filter(is_closed=True).delete()

        # Call API
        response = self.client.get('/orders/daily-report/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should return error with zero amounts
        self.assertIn('error', data)
        self.assertEqual(data['cash_total'], 0.0)
        self.assertEqual(data['card_total'], 0.0)
        self.assertEqual(data['other_total'], 0.0)
        self.assertEqual(data['unpaid_total'], 0.0)
        self.assertEqual(data['paid_total'], 0.0)
        self.assertIn('Hələ bağlanmış hesabat yoxdur', data['message'])

        print("✅ Correctly handles no closed reports")

    def test_api_closed_report_no_orders(self):
        """Test 3: API with closed report but no orders after it"""
        print("\n🧪 TEST 3: API - Closed Report, No New Orders")

        # Create closed report
        closed_report = self.create_closed_statistics_report()

        # Call API (no orders created after report)
        response = self.client.get('/orders/daily-report/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should return zero amounts but no error
        self.assertNotIn('error', data)
        self.assertEqual(data['cash_total'], 0.0)
        self.assertEqual(data['card_total'], 0.0)
        self.assertEqual(data['other_total'], 0.0)
        self.assertEqual(data['unpaid_total'], 0.0)
        self.assertEqual(data['paid_total'], 0.0)
        self.assertIn('last_report_end_time', data)
        self.assertIn('last_report_ended_by', data)

        print("✅ Correctly handles closed report with no new orders")

    def test_api_closed_report_with_orders(self):
        """Test 4: API with closed report and subsequent orders"""
        print("\n🧪 TEST 4: API - Closed Report with New Orders")

        # Create closed report
        closed_report = self.create_closed_statistics_report()

        # Create orders after the report
        test_orders = [
            (Decimal('25.50'), True, 'CASH'),    # Cash payment
            (Decimal('45.00'), True, 'CARD'),    # Card payment
            (Decimal('15.25'), True, 'OTHER'),   # Other payment
            (Decimal('30.00'), False, None),     # Unpaid order
        ]

        orders = self.create_orders_after_report(closed_report, test_orders)

        # Call API
        response = self.client.get('/orders/daily-report/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        print(f"📊 API Response: {json.dumps(data, indent=2, default=str)}")

        # Verify calculations
        expected_cash = 25.50
        expected_card = 45.00
        expected_other = 15.25
        expected_unpaid = 30.00
        expected_paid = expected_cash + expected_card + expected_other

        self.assertAlmostEqual(data['cash_total'], expected_cash, places=2)
        self.assertAlmostEqual(data['card_total'], expected_card, places=2)
        self.assertAlmostEqual(data['other_total'], expected_other, places=2)
        self.assertAlmostEqual(data['unpaid_total'], expected_unpaid, places=2)
        self.assertAlmostEqual(data['paid_total'], expected_paid, places=2)

        print("✅ All payment calculations correct!")

    def test_url_configuration(self):
        """Test 5: Verify URL endpoint is accessible"""
        print("\n🧪 TEST 5: URL Configuration")

        # Test URL endpoint
        response = self.client.get('/orders/daily-report/')
        print(f"📡 GET /orders/daily-report/ → Status: {response.status_code}")

        self.assertEqual(response.status_code, 200)

        # Verify response is valid JSON
        data = response.json()
        self.assertIsInstance(data, dict)

        print("✅ URL endpoint accessible and returns JSON")

    def test_telegram_bot_integration(self):
        """Test 6: Verify telegram bot integration"""
        print("\n🧪 TEST 6: Telegram Bot Integration")

        # Test bot import
        from apps.orders.telegram_bot.bot import RestaurantBot
        print("✅ Bot class imported successfully")

        # Test method exists
        self.assertTrue(hasattr(RestaurantBot, 'show_daily_report'))
        print("✅ show_daily_report method exists")

        # Test menu structure
        import inspect
        menu_source = inspect.getsource(RestaurantBot.orders_menu)
        self.assertIn('Günün Hesabatı', menu_source)
        self.assertIn('daily_report', menu_source)
        print("✅ Menu contains daily report option")

        # Test callback handler
        callback_source = inspect.getsource(RestaurantBot.button_callback)
        self.assertIn('daily_report', callback_source)
        print("✅ Callback handler includes daily_report")

        print("✅ Bot integration complete")

    def test_edge_cases(self):
        """Test 7: Various edge cases"""
        print("\n🧪 TEST 7: Edge Cases")

        # Test with very old closed report
        old_report = self.create_closed_statistics_report(
            hours_ago=24*7)  # 1 week ago

        # Create recent order
        recent_order = Order.objects.create(
            table=self.test_table,
            waitress=self.test_user,
            total_price=Decimal('10.00'),
            is_paid=False,
            created_at=timezone.now() - timedelta(minutes=5)
        )

        # API should still work
        response = self.client.get('/orders/daily-report/')
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['unpaid_total'], 10.0)

        print("✅ Handles old closed reports correctly")
        print("✅ Edge cases handled")


class DailyReportIntegrationTest(TestCase):
    """Integration tests for the complete Daily Report feature"""

    def setUp(self):
        """Setup test data"""
        self.client = Client()
        self.test_user = User.objects.create_user(
            'integration_user',
            'integration@test.com',
            'password123'
        )
        self.test_table = Table.objects.create(number='INT99', capacity=6)

    def test_complete_workflow(self):
        """Test the complete workflow from shift to daily report"""
        print("\n🧪 INTEGRATION TEST: Complete Workflow")

        # 1. Create and close a shift
        shift = Statistics.objects.create(
            title='till_now',
            started_by=self.test_user,
            start_time=timezone.now() - timedelta(hours=4),
            is_closed=False
        )

        # 2. Close the shift
        shift.end_time = timezone.now() - timedelta(hours=1)
        shift.is_closed = True
        shift.ended_by = self.test_user
        shift.save()

        # 3. Create orders after shift closed
        order1 = Order.objects.create(
            table=self.test_table,
            waitress=self.test_user,
            total_price=Decimal('50.00'),
            is_paid=True,
            created_at=timezone.now() - timedelta(minutes=30)
        )

        # 4. Create payment
        payment = Payment.objects.create(
            table=self.test_table,
            total_price=Decimal('50.00'),
            final_price=Decimal('50.00'),
            paid_amount=Decimal('50.00'),
            payment_type='cash',
            paid_by=self.test_user
        )
        payment.orders.add(order1)

        PaymentMethod.objects.create(
            payment=payment,
            amount=Decimal('50.00'),
            payment_type='cash'
        )

        # 5. Test daily report API
        response = self.client.get('/orders/daily-report/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['cash_total'], 50.0)
        self.assertEqual(data['paid_total'], 50.0)

        print("✅ Complete workflow test passed!")
        print("✅ Integration test successful!")
