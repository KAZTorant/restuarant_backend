from django.core.cache import cache
from django.test import TestCase

from apps.meals.models import Meal, MealCategory
from apps.meals.models.meal import MealGroup
from apps.orders.models import OrderItemDeletionLog
from apps.tables.models import Room, Table
from apps.tenants.models import Restaurant


class TenantListCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.alpha = Restaurant.objects.create(name="Alpha", slug="alpha")
        self.beta = Restaurant.objects.create(name="Beta", slug="beta")

        alpha_room = Room.objects.create(
            name="Alpha zal", restaurant=self.alpha, is_active=True,
        )
        beta_room = Room.objects.create(
            name="Beta zal", restaurant=self.beta, is_active=True,
        )
        Table.objects.create(number="1", room=alpha_room)
        Table.objects.create(number="9", room=beta_room)

        alpha_group = MealGroup.objects.create(name="Alpha menu", restaurant=self.alpha)
        beta_group = MealGroup.objects.create(name="Beta menu", restaurant=self.beta)
        alpha_category = MealCategory.objects.create(name="Alpha sub", group=alpha_group)
        beta_category = MealCategory.objects.create(name="Beta sub", group=beta_group)
        Meal.objects.create(name="Alpha meal", price="1.00", category=alpha_category)
        Meal.objects.create(name="Beta meal", price="2.00", category=beta_category)

        self.alpha_category = alpha_category
        self.beta_category = beta_category

    def _get(self, path, slug):
        return self.client.get(path, HTTP_X_RESTAURANT_SLUG=slug)

    def test_rooms_tables_menu_stay_inside_restaurant_after_cache(self):
        first = self._get("/api/tables/rooms/", "alpha")
        second = self._get("/api/tables/rooms/", "beta")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual([row["name"] for row in first.json()], ["Alpha zal"])
        self.assertEqual([row["name"] for row in second.json()], ["Beta zal"])
        self.assertIn("X-Restaurant-Slug", second["Vary"])

        alpha_room_id = first.json()[0]["id"]
        beta_room_id = second.json()[0]["id"]
        alpha_tables = self._get(f"/api/tables/{alpha_room_id}/tables/", "beta")
        beta_tables = self._get(f"/api/tables/{beta_room_id}/tables/", "beta")
        self.assertEqual(alpha_tables.json(), [])
        self.assertEqual([row["number"] for row in beta_tables.json()], ["9"])

        alpha_groups = self._get("/api/meals/groups/", "alpha")
        beta_groups = self._get("/api/meals/groups/", "beta")
        self.assertEqual(
            [row["name"] for row in alpha_groups.json()],
            ["Alpha menu"],
        )
        self.assertEqual(
            alpha_groups.json()[0]["categories"][0]["name"],
            "Alpha sub",
        )
        self.assertEqual(
            [row["name"] for row in beta_groups.json()],
            ["Beta menu"],
        )
        self.assertEqual(
            beta_groups.json()[0]["categories"][0]["name"],
            "Beta sub",
        )

        alpha_meals = self._get(
            f"/api/meals/meals/?meal_category_id={self.alpha_category.id}",
            "alpha",
        )
        beta_looking_at_alpha = self._get(
            f"/api/meals/meals/?meal_category_id={self.alpha_category.id}",
            "beta",
        )
        self.assertEqual([row["name"] for row in alpha_meals.json()], ["Alpha meal"])
        self.assertEqual(beta_looking_at_alpha.json(), [])

    def test_missing_restaurant_does_not_mix_tenants(self):
        response = self.client.get("/api/tables/rooms/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.assertIn("no-store", response["Cache-Control"])


class DeletionLogTenantTests(TestCase):
    def setUp(self):
        self.alpha = Restaurant.objects.create(name="Alpha", slug="alpha")
        self.beta = Restaurant.objects.create(name="Beta", slug="beta")
        alpha_room = Room.objects.create(name="A", restaurant=self.alpha)
        beta_room = Room.objects.create(name="B", restaurant=self.beta)
        self.alpha_table = Table.objects.create(number="1", room=alpha_room)
        self.beta_table = Table.objects.create(number="1", room=beta_room)

    def _log(self, table, meal_name):
        return OrderItemDeletionLog.objects.create(
            order_id=1, order_item_id=1, table_id=table.pk,
            waitress_name="", meal_name=meal_name, quantity=1, price="1.00",
            customer_number=1, reason=OrderItemDeletionLog.REASON_RETURN,
        )

    def test_for_restaurant_excludes_other_restaurant_logs(self):
        self._log(self.alpha_table, "Alpha meal")
        self._log(self.beta_table, "Beta meal")

        alpha_names = list(
            OrderItemDeletionLog.objects.for_restaurant(self.alpha)
            .values_list("meal_name", flat=True)
        )
        self.assertEqual(alpha_names, ["Alpha meal"])
        self.assertEqual(
            OrderItemDeletionLog.objects.for_restaurant(None).count(), 2)
