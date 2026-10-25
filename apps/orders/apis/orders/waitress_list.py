from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.orders.serializers import ListWaitressSerializer
from apps.tenants.utils import filter_by_restaurant
from apps.users.permissions import IsAdmin
from apps.users.models import User


class ListWaitressAPIView(ListAPIView):

    serializer_class = ListWaitressSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return filter_by_restaurant(User.objects.filter(type="waitress"))
