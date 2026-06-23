from django.urls import path

from apps.frontend import views

app_name = 'frontend'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('hall/<int:hall_id>/', views.floor_plan_view, name='floor_plan'),
    path(
        'hall/<int:hall_id>/table/<int:table_id>/',
        views.order_view,
        name='order',
    ),
]
