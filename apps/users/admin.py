from django.utils.html import format_html
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path, reverse
from apps.users.models import ShiftHandover
from django.contrib import admin, messages
from django.contrib import messages
from django.utils import timezone
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.users.models import User
from apps.users.models.shift_handover import ShiftHandover


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'type', 'first_name',
                    'last_name', 'is_staff', 'is_active')
    list_filter = ('type', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', "first_name", "last_name",)}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups',)}),
        ('User Type', {'fields': ('type',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'type', 'is_staff', 'is_active'),
        }),
    )
    search_fields = ('username',)
    ordering = ('username',)


# Register the custom admin class
admin.site.register(User, CustomUserAdmin)

# admin.py


@admin.register(ShiftHandover)
class ShiftHandoverAdmin(admin.ModelAdmin):
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
                return format_html('<span style="color: orange;">⏳ Gözləyir</span>')
        return format_html('<span style="color: green;">✅ Təsdiqləndi</span>')

    confirm_button.short_description = "Əməliyyat"

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
