from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.admin_frontend.decorators import staff_required


@staff_required
def dashboard_view(request):
    return render(request, 'admin_panel/dashboard.html')


@require_http_methods(['GET', 'POST'])
def logout_view(request):
    logout(request)
    return redirect('admin_panel:login')


def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_panel:dashboard')
    error = request.GET.get('error')
    messages = {
        'staff': 'Admin panelinə giriş icazəsi yoxdur',
    }
    return render(request, 'admin_panel/login.html', {
        'error': messages.get(error, ''),
    })


@staff_required
def model_list_view(request, app_label, model_name):
    return render(request, 'admin_panel/model_list.html', {
        'app_label': app_label,
        'model_name': model_name,
    })


@staff_required
def model_form_view(request, app_label, model_name, pk=None):
    return render(request, 'admin_panel/model_form.html', {
        'app_label': app_label,
        'model_name': model_name,
        'pk': pk,
        'is_add': pk is None,
    })


@staff_required
def statistics_view(request):
    return render(request, 'admin_panel/statistics.html')


@staff_required
def summary_view(request):
    return render(request, 'admin_panel/summary.html')


@staff_required
def payment_calculation_view(request):
    return render(request, 'admin_panel/payment_calculation.html')


@staff_required
def tables_view(request):
    return render(request, 'admin_panel/tables.html')


@staff_required
def withdrawn_list_view(request):
    return render(request, 'admin_panel/withdrawn_list.html')
