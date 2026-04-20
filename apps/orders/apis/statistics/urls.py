from django.urls import path

from apps.orders.apis.statistics import (ActiveOrdersStatsAPIView,
                                         CurrentShiftAPIView, EndShiftAPIView,
                                         StartShiftAPIView,
                                         StartShiftInfoAPIView,
                                         StatisticsDetailAPIView,
                                         StatisticsListAPIView)

urlpatterns = [
    # Statistics/Hesabatlar list
    path(
        '',
        StatisticsListAPIView.as_view(),
        name='statistics-list'
    ),
    
    # Statistics detail (all tabs)
    path(
        '<int:shift_id>/',
        StatisticsDetailAPIView.as_view(),
        name='statistics-detail'
    ),
    
    # Current active shift
    path(
        'current-shift/',
        CurrentShiftAPIView.as_view(),
        name='current-shift'
    ),
    
    # Get suggested initial amounts for new shift
    path(
        'start-shift-info/',
        StartShiftInfoAPIView.as_view(),
        name='start-shift-info'
    ),
    
    # Start a new shift
    path(
        'start-shift/',
        StartShiftAPIView.as_view(),
        name='start-shift'
    ),
    
    # End a shift
    path(
        '<int:shift_id>/end-shift/',
        EndShiftAPIView.as_view(),
        name='end-shift'
    ),
    
    # Active orders statistics
    path(
        'active-orders-stats/',
        ActiveOrdersStatsAPIView.as_view(),
        name='active-orders-stats'
    ),
]
