import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.meals.models import Meal

# Get a specific meal
meal = Meal.objects.filter(id=37).first()
if meal:
    print(f"Meal: {meal.name}")
    print(f"Category: {meal.category.name if meal.category else 'None'}")
    print(f"\nPreparation Places (M2M - meals_multi):")
    for place in meal.preparation_places.all():
        print(f"  - {place.name} (ID: {place.id})")
    
    print(f"\nPreparation Place (FK - meals_single):")
    if meal.preparation_place:
        print(f"  - {meal.preparation_place.name} (ID: {meal.preparation_place.id})")
    else:
        print("  - None")
    
    print(f"\nget_all_preparation_places() method:")
    for place in meal.get_all_preparation_places():
        print(f"  - {place.name} (ID: {place.id})")
else:
    print("Meal not found!")
