from django.urls import path

from apps.frontend import views

app_name = 'frontend'

urlpatterns = [
    path('', views.restaurant_list_view, name='restaurant_list'),
    path('r/<slug:slug>/', views.login_view, name='login'),
    path('r/<slug:slug>/logout/', views.logout_view, name='logout'),
    path(
        'r/<slug:slug>/hall/<int:hall_id>/',
        views.floor_plan_view,
        name='floor_plan',
    ),
    path(
        'r/<slug:slug>/hall/<int:hall_id>/table/<int:table_id>/',
        views.order_view,
        name='order',
    ),
]
