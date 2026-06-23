from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Lower


def dedupe_names(apps, schema_editor):
    MealGroup = apps.get_model('meals', 'MealGroup')
    seen = {}
    for group in MealGroup.objects.order_by('restaurant_id', 'name', 'pk'):
        key = (group.restaurant_id, group.name.lower())
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count > 1:
            group.name = f"{group.name} ({count})"
            group.save(update_fields=['name'])

    MealCategory = apps.get_model('meals', 'MealCategory')
    seen = {}
    for category in MealCategory.objects.exclude(group__isnull=True).order_by('group_id', 'name', 'pk'):
        key = (category.group_id, category.name.lower())
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count > 1:
            category.name = f"{category.name} ({count})"
            category.save(update_fields=['name'])

    Meal = apps.get_model('meals', 'Meal')
    seen = {}
    for meal in Meal.objects.exclude(category__isnull=True).order_by('category_id', 'name', 'pk'):
        key = (meal.category_id, meal.name.lower())
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count > 1:
            meal.name = f"{meal.name} ({count})"
            meal.save(update_fields=['name'])


class Migration(migrations.Migration):

    dependencies = [
        ('meals', '0015_restaurant_required'),
    ]

    operations = [
        migrations.RunPython(dedupe_names, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='mealgroup',
            constraint=models.UniqueConstraint(
                Lower('name'),
                'restaurant',
                name='unique_mealgroup_name_ci_per_restaurant',
            ),
        ),
        migrations.AddConstraint(
            model_name='mealcategory',
            constraint=models.UniqueConstraint(
                Lower('name'),
                'group',
                condition=Q(group__isnull=False),
                name='unique_mealcategory_name_ci_per_group',
            ),
        ),
        migrations.AddConstraint(
            model_name='meal',
            constraint=models.UniqueConstraint(
                Lower('name'),
                'category',
                condition=Q(category__isnull=False),
                name='unique_meal_name_ci_per_category',
            ),
        ),
    ]
