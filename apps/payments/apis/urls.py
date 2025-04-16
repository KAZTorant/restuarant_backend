from django.urls import path

from apps.payments.apis import CompleteTablePaymentAPIView


urlpatterns = [
    path(
        '<int:table_id>/pay-orders/',
        CompleteTablePaymentAPIView.as_view(),
        name='print-orders'
    ),
]
