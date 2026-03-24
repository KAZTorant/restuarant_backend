from django.urls import path

from apps.inventory_connector.apis.views import (InventoryItemAddOrUpdateView,
                                                 InventoryItemListView)

urlpatterns = [
    path('inventory-items/add-or-update/', InventoryItemAddOrUpdateView.as_view(), name='inventory-item-add-or-update'),
    path('inventory-items/', InventoryItemListView.as_view(), name='inventory-item-list'),
]
