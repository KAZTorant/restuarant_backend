from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from inventory.models import (InventoryItem, InventoryRecord, InventryCategory,
                              Supplier)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory_connector.apis.serializers import InventoryItemNameSerializer, InventoryItemSerializer


class InventoryItemAddOrUpdateView(APIView):
    """
    API for adding or updating an inventory item based on its name.
    If the item exists (by name), it updates the provided fields.
    If it does not exist, it creates a new item.
    """

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'category', 'unit'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='Name of the inventory item'),
                'category': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the category'),
                'unit': openapi.Schema(type=openapi.TYPE_STRING, description='Unit of measurement (e.g., kg, l, pcs, package)'),
                'supplier': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the supplier (optional)'),
                'quantity': openapi.Schema(type=openapi.TYPE_NUMBER, description='Quantity to add (Miqdar)'),
                'price': openapi.Schema(type=openapi.TYPE_NUMBER, description='Price per unit (optional)'),
            },
        ),
        responses={
            200: InventoryItemSerializer,
            201: InventoryItemSerializer,
            400: 'Bad Request'
        }
    )
    def post(self, request):
        name = request.data.get('name')
        if not name:
            return Response({"error": "Name field is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Try to find the item by name (case-insensitive search could be better, but exact match for now as per requirement)
        # Using filter().first() to avoid MultipleObjectsReturned if inconsistent data exists, 
        # though name should ideally be unique.
        inventory_item = InventoryItem.objects.filter(name=name).first()

        data = request.data.copy()
        quantity = data.get('quantity')
        price = data.get('price', 0)
        
        # If updating, we might not want to change the category if not provided, 
        # but the requirement says "update its given values".
        # Creating serializer with partial=True to allow updating only provided fields.
        
        if inventory_item:
            serializer = InventoryItemSerializer(inventory_item, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                
                # Update quantity if provided
                if quantity is not None:
                    try:
                        qty = float(quantity)
                        if qty > 0:
                            InventoryRecord.objects.create(
                                inventory_item=inventory_item,
                                quantity=qty,
                                record_type='add',
                                reason='adjustment',
                                price=price
                            )
                    except ValueError:
                        pass # Ignore invalid quantity

                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # For creation, we need required fields like category and unit
            # Check if category and unit are provided
            if 'category' not in data or 'unit' not in data:
                 return Response({"error": "Category and unit are required for creating a new item."}, status=status.HTTP_400_BAD_REQUEST)

            serializer = InventoryItemSerializer(data=data)
            if serializer.is_valid():
                item = serializer.save()
                
                # Add initial quantity if provided
                if quantity is not None:
                    try:
                        qty = float(quantity)
                        if qty > 0:
                            InventoryRecord.objects.create(
                                inventory_item=item,
                                quantity=qty,
                                record_type='add',
                                reason='adjustment', # Or 'purchase' for new items
                                price=price
                            )
                    except ValueError:
                        pass # Ignore invalid quantity

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InventoryItemListView(APIView):
    """
    Returns all inventory item names (id, name, unit) without pagination.
    """
    @swagger_auto_schema(
        responses={200: InventoryItemNameSerializer(many=True)}
    )
    def get(self, request):
        items = InventoryItem.objects.all().order_by('name')
        serializer = InventoryItemNameSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        items = InventoryItem.objects.all().order_by('name')
        serializer = InventoryItemNameSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
