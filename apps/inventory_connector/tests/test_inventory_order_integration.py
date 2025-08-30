from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.tables.models import Room, Table
from apps.meals.models import MealGroup, MealCategory, Meal
from apps.printers.models.place import PreparationPlace
from apps.inventory_connector.models import MealInventoryConnector, MealInventoryMapping
from inventory.models import InventryCategory as InvCategory, Supplier as InvSupplier, InventoryItem, InventoryRecord


User = get_user_model()


class InventoryOrderIntegrationTests(TestCase):
    def setUp(self):
        # Users
        self.user = User.objects.create_user(
            username="test", password="pass", type="waitress")
        # Rooms/Tables
        room = Room.objects.create(name="Test Room")
        self.table = Table.objects.create(number="1", capacity=4, room=room)
        # Prep place
        prep = PreparationPlace.objects.create(name="Kitchen")
        # Meals
        group = MealGroup.objects.create(name="Main")
        category = MealCategory.objects.create(name="Plov", group=group)
        self.meal = Meal.objects.create(name="Toyuq plov", price=Decimal(
            "10.00"), category=category, preparation_place=prep)
        # Inventory
        cat = InvCategory.objects.create(name="Əsas", description="")
        sup = InvSupplier.objects.create(name="Supp", contact_info="")
        self.item_rice = InventoryItem.objects.create(
            name="Düyü", category=cat, unit="kq", supplier=sup)
        self.item_chicken = InventoryItem.objects.create(
            name="Toyuq", category=cat, unit="kq", supplier=sup)
        # Connector and mappings: per meal uses 0.2 kg chicken and 0.3 kg rice, price per kg
        connector = MealInventoryConnector.objects.create(meal=self.meal)
        MealInventoryMapping.objects.create(
            connector=connector, inventory_item=self.item_chicken, quantity=Decimal("0.200"), price=Decimal("6.000"))
        MealInventoryMapping.objects.create(
            connector=connector, inventory_item=self.item_rice, quantity=Decimal("0.300"), price=Decimal("2.000"))

        # Seed starting stock via InventoryRecord 'add'
        InventoryRecord.objects.create(inventory_item=self.item_chicken, quantity=Decimal(
            "10.000"), record_type="add", reason="purchase", price=60)
        InventoryRecord.objects.create(inventory_item=self.item_rice, quantity=Decimal(
            "20.000"), record_type="add", reason="purchase", price=40)

    def test_confirm_order_item_deducts_inventory(self):
        from apps.orders.models import Order, OrderItem
        order = Order.objects.create(
            table=self.table, waitress=self.user, is_main=True)
        oi = OrderItem.objects.create(
            order=order, meal=self.meal, quantity=2, price=Decimal("20.00"), confirmed=False)

        # Confirm to trigger deduction via signal
        oi.confirmed = True
        oi.save()

        # Two InventoryRecord entries with record_type='remove' should exist (chicken and rice)
        removes = InventoryRecord.objects.filter(
            record_type='remove', reason='sold')
        self.assertEqual(removes.count(), 2)

        # Quantities deducted should be mapping.qty * order qty
        self.assertTrue(
            removes.filter(inventory_item=self.item_chicken, quantity=Decimal(
                "0.400"), price=Decimal("2.400")).exists()
        )
        self.assertTrue(
            removes.filter(inventory_item=self.item_rice, quantity=Decimal(
                "0.600"), price=Decimal("1.200")).exists()
        )

    def test_unconfirm_returns_inventory(self):
        from apps.orders.models import Order, OrderItem
        order = Order.objects.create(
            table=self.table, waitress=self.user, is_main=True)
        oi = OrderItem.objects.create(
            order=order, meal=self.meal, quantity=1, price=Decimal("10.00"), confirmed=True)
        # Initial confirm created remove records
        self.assertEqual(InventoryRecord.objects.filter(
            record_type='remove', reason='sold').count(), 2)

        # Now unconfirm to add back
        oi.confirmed = False
        oi.save()
        adds = InventoryRecord.objects.filter(
            record_type='add', reason='return')
        self.assertEqual(adds.count(), 2)
        self.assertTrue(adds.filter(
            inventory_item=self.item_chicken, quantity=Decimal("0.200")).exists())
        self.assertTrue(adds.filter(inventory_item=self.item_rice,
                        quantity=Decimal("0.300")).exists())

    def test_quantity_increase_removes_more(self):
        from apps.orders.models import Order, OrderItem
        order = Order.objects.create(
            table=self.table, waitress=self.user, is_main=True)
        oi = OrderItem.objects.create(
            order=order, meal=self.meal, quantity=1, price=Decimal("10.00"), confirmed=True)
        # Increase quantity to 3 -> diff 2 should remove extra stock
        oi.quantity = 3
        oi.save()
        removes = InventoryRecord.objects.filter(
            record_type='remove', reason='sold')
        # Initial 2 removes + diff 2 removes = 4 total remove records
        self.assertEqual(removes.count(), 4)
        self.assertTrue(removes.filter(
            inventory_item=self.item_chicken, quantity=Decimal("0.400")).exists())
        self.assertTrue(removes.filter(
            inventory_item=self.item_rice, quantity=Decimal("0.600")).exists())

    def test_delete_confirmed_item_adds_back(self):
        from apps.orders.models import Order, OrderItem
        order = Order.objects.create(
            table=self.table, waitress=self.user, is_main=True)
        oi = OrderItem.objects.create(
            order=order, meal=self.meal, quantity=2, price=Decimal("20.00"), confirmed=True)
        # Delete with default delete (should add back)
        oi.delete(reason='return')
        adds = InventoryRecord.objects.filter(record_type='add')
        self.assertTrue(adds.filter(inventory_item=self.item_chicken,
                        quantity=Decimal("0.400"), reason='return').exists())
        self.assertTrue(adds.filter(inventory_item=self.item_rice,
                        quantity=Decimal("0.600"), reason='return').exists())
