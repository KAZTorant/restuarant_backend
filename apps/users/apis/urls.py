from django.urls import path

from apps.users.apis import NetworkAPIView, PinLoginAPIView, WhatsAppDeliveryView

urlpatterns = [
    path(
        "login/",
        PinLoginAPIView.as_view(),
    ),
    path(
        "network-ip/",
        NetworkAPIView.as_view(),
    ),
    path(
        "whatsapp-delivery/",
        WhatsAppDeliveryView.as_view(),
        name="whatsapp-delivery",
    ),
]
