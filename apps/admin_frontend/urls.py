from django.urls import path

from apps.admin_frontend import views

app_name = 'admin_panel'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('', views.dashboard_view, name='dashboard'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('summary/', views.summary_view, name='summary'),
    path('payment-calculation/', views.payment_calculation_view, name='payment_calculation'),
    path('tables/', views.tables_view, name='tables'),
    path('withdrawn-list/', views.withdrawn_list_view, name='withdrawn_list'),
    path('models/<str:app_label>/<str:model_name>/', views.model_list_view, name='model_list'),
    path('models/<str:app_label>/<str:model_name>/add/', views.model_form_view, name='model_add'),
    path(
        'models/<str:app_label>/<str:model_name>/<int:pk>/change/',
        views.model_form_view,
        name='model_change',
    ),
]
