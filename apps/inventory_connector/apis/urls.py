from django.urls import path
from .views import InventoryItemAddOrUpdateView

urlpatterns = [
    path('inventory-items/add-or-update/', InventoryItemAddOrUpdateView.as_view(), name='inventory-item-add-or-update'),
]
