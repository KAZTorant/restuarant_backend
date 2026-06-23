import socket

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.frontend.decorators import pin_login_required
from apps.tables.models import Room
from apps.tenants.models import Restaurant

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
        'restaurant_slug': request.session.get('restaurant_slug', ''),
    }


def _role_display_name(role):
    mapping = {
        'admin': 'Adminstrator',
        'waitress': 'Ofsiant',
        'captain_waitress': 'Ofsiant',
        'restaurant': 'Admin',
    }
    return mapping.get(role, role)


def _get_restaurant(slug):
    return get_object_or_404(Restaurant, slug=slug, is_active=True)


def _rooms_for_restaurant(restaurant):
    return Room.objects.filter(restaurant=restaurant, is_active=True)


@require_http_methods(['GET'])
def restaurant_list_view(request):
    restaurants = Restaurant.objects.filter(is_active=True).order_by('name')
    if restaurants.count() == 1:
        return redirect('frontend:login', slug=restaurants.first().slug)
    return render(request, 'frontend/restaurant_list.html', {
        'restaurants': restaurants,
    })


@require_http_methods(['GET', 'POST'])
def login_view(request, slug):
    restaurant = _get_restaurant(slug)

    if request.session.get('authenticated') and request.session.get('restaurant_slug') == slug:
        first_hall = _rooms_for_restaurant(restaurant).order_by('id').first()
        if first_hall:
            return redirect('frontend:floor_plan', slug=slug, hall_id=first_hall.id)
        return redirect('frontend:login', slug=slug)

    error = None
    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()
        if not pin:
            error = 'PIN kod boş ola bilməz.'
        else:
            try:
                user = User.objects.get(username=pin, restaurant=restaurant)
                if not user.is_active:
                    error = 'Hesabınız deaktiv edilib. Administratorla əlaqə saxlayın.'
                else:
                    request.session['authenticated'] = True
                    request.session['pin'] = user.username
                    request.session['role'] = user.type
                    request.session['full_name'] = user.get_full_name()
                    request.session['restaurant_id'] = restaurant.id
                    request.session['restaurant_slug'] = restaurant.slug
                    first_hall = _rooms_for_restaurant(restaurant).order_by('id').first()
                    if first_hall:
                        return redirect(
                            'frontend:floor_plan',
                            slug=slug,
                            hall_id=first_hall.id,
                        )
                    error = 'Heç bir aktiv zal tapılmadı.'
            except User.DoesNotExist:
                error = 'Daxil etdiyiniz PIN kodu yanlışdır. Yenidən cəhd edin.'

    port = settings.BACKEND_PORT
    network_ip = _get_network_ip()
    qr_url = f'http://{network_ip}:{port}/r/{slug}/'

    return render(request, 'frontend/login.html', {
        'error': error,
        'qr_url': qr_url,
        'restaurant': restaurant,
        'restaurant_slug': slug,
    })


@require_http_methods(['GET'])
def logout_view(request, slug):
    request.session.flush()
    return redirect('frontend:login', slug=slug)


@pin_login_required
@require_http_methods(['GET'])
def floor_plan_view(request, slug, hall_id):
    restaurant = _get_restaurant(slug)
    if request.session.get('restaurant_slug') != slug:
        return redirect('frontend:login', slug=slug)

    if not _rooms_for_restaurant(restaurant).filter(pk=hall_id).exists():
        first_hall = _rooms_for_restaurant(restaurant).order_by('id').first()
        if first_hall:
            return redirect('frontend:floor_plan', slug=slug, hall_id=first_hall.id)
        return redirect('frontend:login', slug=slug)

    return render(request, 'frontend/floor_plan.html', {
        'hall_id': hall_id,
        'restaurant_slug': slug,
        'restaurant_name': restaurant.name,
        'role_display_name': _role_display_name(request.session.get('role')),
        **_auth_context(request),
    })


@pin_login_required
@require_http_methods(['GET'])
def order_view(request, slug, hall_id, table_id):
    restaurant = _get_restaurant(slug)
    if request.session.get('restaurant_slug') != slug:
        return redirect('frontend:login', slug=slug)

    return render(request, 'frontend/order.html', {
        'hall_id': hall_id,
        'table_id': table_id,
        'restaurant_slug': slug,
        'restaurant_name': restaurant.name,
        'role_display_name': _role_display_name(request.session.get('role')),
        **_auth_context(request),
    })
