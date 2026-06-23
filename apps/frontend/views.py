import socket

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.frontend.decorators import pin_login_required
from apps.tables.models import Room

User = get_user_model()


def _get_network_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('8.8.8.8', 80))
        ip_address = sock.getsockname()[0]
        sock.close()
        return ip_address
    except OSError:
        return '127.0.0.1'


def _auth_context(request):
    return {
        'pin': request.session.get('pin', ''),
        'role': request.session.get('role', ''),
        'full_name': request.session.get('full_name', ''),
    }


def _role_display_name(role):
    mapping = {
        'admin': 'Adminstrator',
        'waitress': 'Ofsiant',
        'captain_waitress': 'Ofsiant',
        'restaurant': 'Admin',
    }
    return mapping.get(role, role)


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.session.get('authenticated'):
        first_hall = Room.objects.filter(is_active=True).order_by('id').first()
        if first_hall:
            return redirect('frontend:floor_plan', hall_id=first_hall.id)
        return redirect('frontend:login')

    error = None
    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()
        if not pin:
            error = 'PIN kod boş ola bilməz.'
        else:
            try:
                user = User.objects.get(username=pin)
                if not user.is_active:
                    error = 'Hesabınız deaktiv edilib. Administratorla əlaqə saxlayın.'
                else:
                    request.session['authenticated'] = True
                    request.session['pin'] = user.username
                    request.session['role'] = user.type
                    request.session['full_name'] = user.get_full_name()
                    first_hall = Room.objects.filter(
                        is_active=True
                    ).order_by('id').first()
                    if first_hall:
                        return redirect(
                            'frontend:floor_plan',
                            hall_id=first_hall.id,
                        )
                    error = 'Heç bir aktiv zal tapılmadı.'
            except User.DoesNotExist:
                error = 'Daxil etdiyiniz PIN kodu yanlışdır. Yenidən cəhd edin.'

    port = settings.BACKEND_PORT
    network_ip = _get_network_ip()
    qr_url = f'http://{network_ip}:{port}/'

    return render(request, 'frontend/login.html', {
        'error': error,
        'qr_url': qr_url,
    })


@require_http_methods(['GET'])
def logout_view(request):
    request.session.flush()
    return redirect('frontend:login')


@pin_login_required
@require_http_methods(['GET'])
def floor_plan_view(request, hall_id):
    return render(request, 'frontend/floor_plan.html', {
        'hall_id': hall_id,
        'role_display_name': _role_display_name(request.session.get('role')),
        **_auth_context(request),
    })


@pin_login_required
@require_http_methods(['GET'])
def order_view(request, hall_id, table_id):
    return render(request, 'frontend/order.html', {
        'hall_id': hall_id,
        'table_id': table_id,
        'role_display_name': _role_display_name(request.session.get('role')),
        **_auth_context(request),
    })
