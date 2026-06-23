import json

from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse

from apps.tenants.forms import RestaurantImportForm
from apps.tenants.admin_utils import get_user_restaurant
from apps.tenants.import_export import import_restaurant_data
from apps.tenants.models import Restaurant


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'phone', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug', 'phone')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'is_active'),
        }),
        ('Əlaqə', {
            'fields': ('address', 'phone', 'owner_phone'),
        }),
        ('Tarixlər', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        restaurant = get_user_restaurant(request.user)
        if restaurant:
            return qs.filter(pk=restaurant.pk)
        return qs

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return super().has_change_permission(request, obj)
        restaurant = get_user_restaurant(request.user)
        if obj is None:
            return restaurant is not None
        return restaurant is not None and obj.pk == restaurant.pk

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/import-data/',
                self.admin_site.admin_view(self.import_data_view),
                name='tenants_restaurant_import_data',
            ),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_url'] = reverse(
            'admin:tenants_restaurant_import_data',
            args=[object_id],
        )
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )

    def import_data_view(self, request, object_id):
        restaurant = self.get_object(request, object_id)
        if restaurant is None:
            self.message_user(request, 'Restoran tapılmadı.', level=messages.ERROR)
            return redirect('admin:tenants_restaurant_changelist')

        if request.method == 'POST':
            form = RestaurantImportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    content = form.cleaned_data['import_file'].read().decode('utf-8')
                    payload = json.loads(content)
                    import_restaurant_data(restaurant, payload)
                    self.message_user(
                        request,
                        f'"{restaurant.name}" üçün məlumatlar uğurla import edildi.',
                        level=messages.SUCCESS,
                    )
                    return redirect(
                        'admin:tenants_restaurant_change',
                        object_id=restaurant.pk,
                    )
                except (json.JSONDecodeError, ValueError, KeyError) as exc:
                    self.message_user(
                        request,
                        f'Import xətası: {exc}',
                        level=messages.ERROR,
                    )
        else:
            form = RestaurantImportForm()

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'form': form,
            'restaurant': restaurant,
            'title': f'DB Import — {restaurant.name}',
        }
        return render(request, 'admin/tenants/restaurant/import_data.html', context)
