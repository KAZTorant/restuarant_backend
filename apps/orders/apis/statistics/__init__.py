from apps.orders.apis.statistics.active_orders import ActiveOrdersStatsAPIView
from apps.orders.apis.statistics.detail import StatisticsDetailAPIView
from apps.orders.apis.statistics.list import StatisticsListAPIView
from apps.orders.apis.statistics.shift import (CurrentShiftAPIView, EndShiftAPIView, StartShiftAPIView,
                    StartShiftInfoAPIView)

__all__ = [
    'StatisticsListAPIView',
    'StatisticsDetailAPIView',
    'CurrentShiftAPIView',
    'StartShiftAPIView',
    'EndShiftAPIView',
    'StartShiftInfoAPIView',
    'ActiveOrdersStatsAPIView',
]
