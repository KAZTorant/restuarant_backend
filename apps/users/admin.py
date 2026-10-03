from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

import requests

from apps.tenants.admin_utils import strip_field_from_fieldsets
from apps.tenants.mixins import TenantAdminMixin
from apps.tenants.models import Restaurant
from apps.users.models import ShiftHandover, User, WhatsAppConfig, WhatsAppMessage, WhatsAppSession
from apps.users.models.whatsapp_session import touch_whatsapp_session


class CustomUserAdmin(TenantAdminMixin, UserAdmin):
    list_display = ('username', 'type', 'restaurant', 'first_name',
                    'last_name', 'is_staff', 'is_active')
    list_filter = ('type', 'restaurant', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', "first_name", "last_name", 'restaurant')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups',)}),
        ('User Type', {'fields': ('type',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'type', 'restaurant', 'is_staff', 'is_active'),
        }),
    )
    search_fields = ('username',)
    ordering = ('username',)

    def get_add_fieldsets(self, request):
        if request.user.is_superuser:
            return self.add_fieldsets
        return strip_field_from_fieldsets(self.add_fieldsets, 'restaurant')

    def get_fieldsets(self, request, obj=None):
        if obj is None and not request.user.is_superuser:
            return self.get_add_fieldsets(request)
        return super().get_fieldsets(request, obj)


# Register the custom admin class
admin.site.register(User, CustomUserAdmin)


@admin.register(WhatsAppConfig)
class WhatsAppConfigAdmin(TenantAdminMixin, admin.ModelAdmin):
    """
    WhatsApp notification recipients. Restaurant staff can manage their own restaurant.
    """
    list_display = ('phone', 'name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('phone', 'name')
    ordering = ('-is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    change_list_template = 'admin/users/whatsappconfig/change_list.html'

    def get_urls(self):
        custom = [
            path(
                'connection/',
                self.admin_site.admin_view(self.connection_view),
                name='whatsapp_connection',
            ),
            path(
                'connection/qr.png',
                self.admin_site.admin_view(self.qr_image_view),
                name='whatsapp_qr',
            ),
            path(
                'connection/logout/',
                self.admin_site.admin_view(self.logout_view),
                name='whatsapp_logout',
            ),
        ]
        return custom + super().get_urls()

    def _service_headers(self):
        key = getattr(settings, 'WHATSAPP_API_KEY', '') or ''
        if key:
            return {'X-API-Key': key}
        return {}

    def _service_base(self):
        return getattr(settings, 'WHATSAPP_SERVICE_URL', 'http://localhost:3001').rstrip('/')

    def _format_phone(self, digits):
        raw = ''.join(ch for ch in str(digits or '') if ch.isdigit())
        if raw.startswith('994') and len(raw) == 12:
            return f'+{raw[:3]} {raw[3:5]} {raw[5:8]} {raw[8:10]} {raw[10:]}'
        return f'+{raw}' if raw else ''

    def _connection_restaurant(self, request):
        user = request.user
        if user.is_superuser:
            slug = (request.POST.get('restaurant') or request.GET.get('restaurant') or '').strip()
            if slug:
                return Restaurant.objects.filter(slug=slug, is_active=True).first()
            current = getattr(request, 'restaurant', None)
            if current is not None and current.is_active and not getattr(request.user, 'restaurant_id', None):
                return current
            return None
        if getattr(user, 'restaurant_id', None):
            return user.restaurant
        return None

    def _connection_redirect(self, request, restaurant):
        url = reverse('admin:whatsapp_connection')
        if request.user.is_superuser and restaurant is not None:
            url = f'{url}?restaurant={restaurant.slug}'
        return redirect(url)

    def connection_view(self, request):
        restaurant = self._connection_restaurant(request)
        base = self._service_base()
        context = {
            **self.admin_site.each_context(request),
            'title': (
                f'{restaurant.name} — WhatsApp qoşulması'
                if restaurant is not None
                else 'Restoran WhatsApp qoşulması'
            ),
            'opts': self.model._meta,
            'service_url': base,
            'restaurant': restaurant,
            'restaurant_slug': restaurant.slug if restaurant else '',
            'restaurants': (
                list(Restaurant.objects.filter(is_active=True).order_by('name'))
                if request.user.is_superuser
                else []
            ),
            'show_picker': request.user.is_superuser,
            'ready': False,
            'authenticating': False,
            'qr_available': False,
            'connected_number': '',
            'status_message': '',
            'error': '',
            'unreachable': False,
        }
        if restaurant is None:
            if not request.user.is_superuser:
                context['error'] = 'Bu istifadəçinin restoranı yoxdur.'
            return render(request, 'admin/users/whatsappconfig/connection.html', context)
        try:
            response = requests.get(
                f'{base}/status',
                params={'restaurant': restaurant.slug, 'start': '1'},
                headers=self._service_headers(),
                timeout=8,
            )
            if response.status_code == 200:
                data = response.json()
                context['ready'] = bool(data.get('ready'))
                context['authenticating'] = bool(data.get('authenticating'))
                context['qr_available'] = bool(data.get('qr_available'))
                context['connected_number'] = (
                    data.get('connected_number_display')
                    or self._format_phone(data.get('connected_number'))
                )
                context['status_message'] = data.get('message') or ''
                context['error'] = data.get('last_error') or ''
                if context['ready'] and data.get('connected_number'):
                    touch_whatsapp_session(restaurant, phone=data.get('connected_number'))
            else:
                context['error'] = f'Servis cavabı: {response.status_code}'
        except requests.RequestException as exc:
            context['unreachable'] = True
            context['error'] = (
                'WhatsApp servisinə qoşulmaq olmadı. '
                f'WHATSAPP_SERVICE_URL={base}. {exc}'
            )
        return render(request, 'admin/users/whatsappconfig/connection.html', context)

    def qr_image_view(self, request):
        restaurant = self._connection_restaurant(request)
        if restaurant is None:
            return HttpResponse(status=400)
        base = self._service_base()
        try:
            response = requests.get(
                f'{base}/qr.png',
                params={'restaurant': restaurant.slug},
                headers=self._service_headers(),
                timeout=8,
            )
        except requests.RequestException:
            return HttpResponse(status=502)
        if response.status_code != 200:
            return HttpResponse(status=response.status_code)
        return HttpResponse(response.content, content_type='image/png')

    def logout_view(self, request):
        restaurant = self._connection_restaurant(request)
        if request.method != 'POST':
            return self._connection_redirect(request, restaurant)
        if restaurant is None:
            self.message_user(request, 'Restoran seçilməyib.', level=messages.ERROR)
            return self._connection_redirect(request, None)
        base = self._service_base()
        try:
            response = requests.post(
                f'{base}/logout',
                json={'restaurant': restaurant.slug},
                headers=self._service_headers(),
                timeout=30,
            )
            if response.status_code == 200:
                touch_whatsapp_session(restaurant, logout=True)
                self.message_user(
                    request,
                    f'{restaurant.name} WhatsApp sessiyası silindi. Yeni QR bir azdan çıxacaq.',
                )
            else:
                self.message_user(
                    request,
                    f'Sessiya silinmədi. Servis cavabı: {response.status_code}',
                    level=messages.ERROR,
                )
        except requests.RequestException as exc:
            self.message_user(request, f'Sessiya silinmədi: {exc}', level=messages.ERROR)
        return self._connection_redirect(request, restaurant)

    def changelist_view(self, request, extra_context=None):
        extra = dict(extra_context or {})
        if not request.user.is_superuser and getattr(request.user, 'restaurant_id', None):
            session = WhatsAppSession.objects.filter(restaurant=request.user.restaurant).first()
            extra['linked_checked'] = True
            extra['linked_whatsapp'] = self._format_phone(session.phone) if session and session.phone else ''
        return super().changelist_view(request, extra)

    def _staff_can_manage(self, request):
        user = request.user
        if not user.is_active or not user.is_staff:
            return False
        if user.is_superuser:
            return True
        return bool(getattr(user, 'restaurant_id', None))

    def has_module_permission(self, request):
        return self._staff_can_manage(request) or super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return self._staff_can_manage(request) or super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return self._staff_can_manage(request) or super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return self._staff_can_manage(request) or super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._staff_can_manage(request) or super().has_delete_permission(request, obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_active and user.is_staff and not user.is_superuser and not getattr(user, 'restaurant_id', None):
            return qs.none()
        return qs


class _WhatsAppReadOnlyAdmin(TenantAdminMixin, admin.ModelAdmin):
    def _staff_can_manage(self, request):
        user = request.user
        if not user.is_active or not user.is_staff:
            return False
        if user.is_superuser:
            return True
        return bool(getattr(user, 'restaurant_id', None))

    def has_module_permission(self, request):
        return self._staff_can_manage(request)

    def has_view_permission(self, request, obj=None):
        return self._staff_can_manage(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(_WhatsAppReadOnlyAdmin):
    list_display = (
        'recipient_phone',
        'recipient_name',
        'status',
        'kind',
        'from_number',
        'sent_at',
        'delivered_at',
        'read_at',
        'created_at',
    )
    list_filter = ('status', 'kind', 'created_at')
    search_fields = ('recipient_phone', 'recipient_name', 'from_number', 'body', 'wa_message_id')
    ordering = ('-created_at',)
    readonly_fields = (
        'restaurant',
        'recipient_phone',
        'recipient_name',
        'from_number',
        'body',
        'kind',
        'status',
        'last_ack',
        'wa_message_id',
        'order_id',
        'error',
        'sent_at',
        'delivered_at',
        'read_at',
        'created_at',
        'updated_at',
    )


@admin.register(WhatsAppSession)
class WhatsAppSessionAdmin(_WhatsAppReadOnlyAdmin):
    list_display = ('phone', 'connected_at', 'updated_at')
    readonly_fields = ('restaurant', 'phone', 'connected_at', 'updated_at')
    ordering = ('-updated_at',)


# admin.py


@admin.register(ShiftHandover)
class ShiftHandoverAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        "from_user", "to_user", "shift_start", "shift_end",
        "cash_in_kassa", "expected_cash", "discrepancy",
        "confirmed_at", "created_at",
        "confirm_button"
    )
    list_filter = ("is_confirmed", "from_user", "to_user")
    search_fields = ("from_user__username",
                     "to_user__username", "from_notes", "to_notes")
    readonly_fields = ("created_at",)
    fields = []  # Will be defined via get_fieldsets

    def get_fieldsets(self, request, obj=None):
        # NEW RECORD: from_user creates the handover
        if not obj:
            return (
                ("Növbə Məlumatları", {
                    "fields": [
                        "to_user", "shift_start", "shift_end",
                        "cash_in_kassa", "from_notes"
                    ]
                }),
            )
        # EXISTING RECORD: if the logged-in user is the from_user (sender)
        if request.user == obj.from_user:
            if not obj.is_confirmed:
                return (
                    ("Növbə Məlumatları (Göndərən)", {
                        "fields": [
                            "to_user", "shift_start", "shift_end",
                            "cash_in_kassa", "from_notes"
                        ]
                    }),
                )
            else:
                # Already confirmed – show complete details as read-only
                return (
                    ("Növbə Məlumatları (Təsdiqlənib)", {
                        "fields": [
                            "from_user", "to_user", "shift_start", "shift_end",
                            "cash_in_kassa", "expected_cash", "discrepancy",
                            "from_notes", "to_notes",
                            "confirmed_at", "created_at"
                        ]
                    }),
                )
        # EXISTING RECORD: if the logged-in user is the to_user (receiver)
        elif request.user == obj.to_user:
            if not obj.is_confirmed:
                return (
                    ("Növbə Təsdiqləmə (Qəbul edən)", {
                        "fields": [
                            "expected_cash", "to_notes"
                        ]
                    }),
                )
            else:
                return (
                    ("Növbə Məlumatları (Təsdiqlənib)", {
                        "fields": [
                            "from_user", "to_user", "shift_start", "shift_end",
                            "cash_in_kassa", "expected_cash", "discrepancy",
                            "from_notes", "to_notes",
                            "confirmed_at", "created_at"
                        ]
                    }),
                )
        # For any other user or superusers, show a complete read-only view.
        return (
            ("Tam Baxış (Təsdiqlənib və ya fərqli istifadəçi)", {
                "fields": [
                    "from_user", "to_user", "shift_start", "shift_end",
                    "cash_in_kassa", "expected_cash", "discrepancy",
                    "from_notes", "to_notes",
                    "confirmed_at", "created_at"
                ]
            }),
        )

    def get_readonly_fields(self, request, obj=None):
        # For new objects, these fields are read-only.
        if not obj:
            return ["is_confirmed", "confirmed_at", "discrepancy", "created_at"]
        ro = ["created_at", "from_user", "discrepancy"]
        if obj.is_confirmed:
            ro += [
                "to_user", "shift_start", "shift_end",
                "cash_in_kassa", "expected_cash", "from_notes", "to_notes",
                "confirmed_at", "created_at"
            ]
        else:
            if request.user == obj.from_user:
                ro += ["expected_cash", "to_notes",
                       "confirmed_at"]
            elif request.user == obj.to_user:
                ro += ["from_user", "shift_start", "shift_end",
                       "cash_in_kassa", "from_notes"]
        return ro

    @admin.display(description="Əməliyyat")
    def confirm_button(self, obj):
        """
        Renders a styled 'Təsdiqlə' button if not yet confirmed and to_user is current user.
        Otherwise shows a waiting or confirmed icon.
        """
        if hasattr(self, 'request'):
            if not obj.is_confirmed and self.request.user == obj.to_user:
                url = reverse("admin:shifthandover_confirm", args=[obj.id])
                return format_html(
                    '<a href="{}" style="'
                    'background-color: #28a745; '
                    'color: white; padding: 5px 10px; '
                    'border-radius: 4px; text-decoration: none; '
                    'font-weight: bold;">Təsdiqlə</a>', url
                )
            elif not obj.is_confirmed:
                return mark_safe('<span style="color: orange;">⏳ Gözləyir</span>')
        return mark_safe('<span style="color: green;">✅ Təsdiqləndi</span>')


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'confirm/<int:handover_id>/',
                self.admin_site.admin_view(self.process_confirm),
                name="shifthandover_confirm"
            ),
        ]
        return custom_urls + urls

    def process_confirm(self, request, handover_id):
        """
        Process the confirmation request via the Confirm button.
        Only the designated to_user can confirm.
        Additional checks:
        - to_user must have entered expected_cash.
        - from_user and to_user must be userType 'admin'.
        """
        handover = get_object_or_404(ShiftHandover, id=handover_id)

        if handover.is_confirmed:
            self.message_user(
                request, "Bu növbə təslimi artıq təsdiqlənib.", level=messages.WARNING)

        elif request.user != handover.to_user:
            self.message_user(
                request, "Bu əməliyyatı etmək üçün icazəniz yoxdur.", level=messages.ERROR)

        elif handover.expected_cash is None:
            self.message_user(
                request, "Təsdiqləmək üçün əvvəlcə gözlənilən məbləği daxil edin.", level=messages.ERROR)

        elif handover.from_user.type != "admin" or handover.to_user.type != "admin":
            self.message_user(
                request, "Yalnız 'admin' istifadəçiləri növbə təslimi edə bilər.", level=messages.ERROR)

        else:
            handover.is_confirmed = True
            handover.confirmed_at = timezone.now()
            handover.save(update_fields=["is_confirmed", "confirmed_at"])
            self.message_user(
                request, "Növbə təslimi təsdiqləndi.", level=messages.SUCCESS)

        return redirect(reverse("admin:users_shifthandover_changelist"))

    def changelist_view(self, request, extra_context=None):
        # Store request so that confirm_button can access it
        self.request = request
        return super().changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.from_user = request.user
        super().save_model(request, obj, form, change)
