from django.urls import path

# Import your new API view
from apps.orders.api_views import active_orders_api, daily_report_api, period_report_api
from apps.orders.apis import (AddOrderItemAPIView, ChangeTableOrderAPIView,
                              ChangeWaitressAPIView, CheckOrderAPIView,
                              CloseTableOrderAPIView, CreateOrderAPIView,
                              DeleteOrderItemAPIView, JoinTableOrdersAPIView,
                              ListOrderItemsAPIView, ListTableOrdersAPIView,
                              ListWaitressAPIView)
from apps.orders.apis.order_items.comment import AddCommentToOrderItemAPIView
from apps.orders.apis.order_items.transfer import TransferOrderItemsAPIView
from apps.orders.apis.orders.confirm import \
    ConfirmOrderItemsToWorkerPrintersAPIView
from apps.printers.apis import PrintCheckAPIView

urlpatterns = [
    # Add your new API endpoint at the top
    path(
        'active-orders/',
        active_orders_api,
        name='active-orders'
    ),

    path(
        'daily-report/',
        daily_report_api,
        name='daily-report'
    ),

    path(
        'period-report/',
        period_report_api,
        name='period-report'
    ),

    path(
        '<int:table_id>/check-status/',
        CheckOrderAPIView.as_view(),
        name='check-table-status'
    ),

    path(
        '<int:table_id>/create/',
        CreateOrderAPIView.as_view(),
        name='create-order'
    ),

    path(
        '<int:table_id>/add-order-item/',
        AddOrderItemAPIView.as_view(),
        name='add-order-item'
    ),
    path(
        '<int:table_id>/tranfer-order-items/',
        TransferOrderItemsAPIView.as_view(),
        name='add-order-item'
    ),


    path(
        '<int:table_id>/delete-order-item/',
        DeleteOrderItemAPIView.as_view(),
        name='delete-order-item'
    ),

    path(
        '<int:table_id>/list-order-items/',
        ListOrderItemsAPIView.as_view(),
        name='list-order-items'
    ),

    path(
        '<int:table_id>/list-orders/',
        ListTableOrdersAPIView.as_view(),
        name='list-orders'
    ),

    path(
        '<int:table_id>/change-table-for-order/',
        ChangeTableOrderAPIView.as_view(),
        name='change-table-for-order'
    ),

    path(
        '<int:table_id>/join-tables-orders/',
        JoinTableOrdersAPIView.as_view(),
        name='join-tables-orders'
    ),

    path(
        '<int:table_id>/close-table-for-order/',
        CloseTableOrderAPIView.as_view(),
        name='close-table-for-order'
    ),

    path(
        'list-waitress/',
        ListWaitressAPIView.as_view(),
        name='list-waitress'
    ),

    path(
        '<int:table_id>/change-waitress/',
        ChangeWaitressAPIView.as_view(),
        name='change-waitress'
    ),

    path(
        '<int:table_id>/print-check/',
        PrintCheckAPIView.as_view(),
        name='print-check'
    ),

    path(
        '<int:table_id>/confirm/',
        ConfirmOrderItemsToWorkerPrintersAPIView.as_view(),
        name='confirm'
    ),

    path(
        '<int:table_id>/comment/',
        AddCommentToOrderItemAPIView.as_view(),
        name='comment'
    ),
]
