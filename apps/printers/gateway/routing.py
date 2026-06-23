from django.urls import re_path

from apps.printers.gateway.consumers import PrintGatewayConsumer

websocket_urlpatterns = [
    re_path(r'ws/print-gateway/$', PrintGatewayConsumer.as_asgi()),
]
