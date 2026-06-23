"""Django admin registry helpers for the admin API."""

from django.contrib import admin
from django.contrib.admin.sites import AdminSite


def get_model_admin(app_label: str, model_name: str):
    """Return ModelAdmin instance for app/model or raise LookupError."""
    model_name = model_name.lower()
    for model, model_admin in admin.site._registry.items():
        if model._meta.app_label == app_label and model._meta.model_name == model_name:
            return model, model_admin
    raise LookupError(f'No admin registered for {app_label}.{model_name}')


def iter_registered_models():
    """Yield (app_label, model_name, model, model_admin) for all registered models."""
    seen = set()
    for model, model_admin in admin.site._registry.items():
        key = (model._meta.app_label, model._meta.model_name)
        if key in seen:
            continue
        seen.add(key)
        yield model._meta.app_label, model._meta.model_name, model, model_admin


def build_navigation(user):
    """Build sidebar navigation tree grouped by app."""
    jazzmin_order = _get_jazzmin_order()
    apps = {}

    for app_label, model_name, model, model_admin in iter_registered_models():
        if not model_admin.has_view_permission(_FakeRequest(user)):
            continue

        app_config = model._meta.app_config
        app_verbose = getattr(app_config, 'verbose_name', app_label)
        app_key = app_label

        if app_key not in apps:
            apps[app_key] = {
                'app_label': app_label,
                'name': str(app_verbose),
                'models': [],
                'order': jazzmin_order.get(app_label, 999),
            }

        perms = {
            'view': model_admin.has_view_permission(_FakeRequest(user)),
            'add': model_admin.has_add_permission(_FakeRequest(user)),
            'change': model_admin.has_change_permission(_FakeRequest(user)),
            'delete': model_admin.has_delete_permission(_FakeRequest(user)),
        }

        custom_list = getattr(model_admin, 'change_list_template', None)
        custom_form = getattr(model_admin, 'change_form_template', None)

        apps[app_key]['models'].append({
            'app_label': app_label,
            'model_name': model_name,
            'name': str(model._meta.verbose_name_plural),
            'singular_name': str(model._meta.verbose_name),
            'permissions': perms,
            'has_custom_list': bool(custom_list and 'admin/' in str(custom_list)),
            'has_custom_form': bool(custom_form),
        })

    result = sorted(apps.values(), key=lambda a: (a['order'], a['name']))
    for app in result:
        app['models'].sort(key=lambda m: m['name'])
    return result


def _get_jazzmin_order():
    try:
        from django.conf import settings
        order = settings.JAZZMIN_SETTINGS.get('order_with_respect_to', [])
        return {name: idx for idx, name in enumerate(order)}
    except Exception:
        return {}


class _FakeRequest:
    """Minimal request stub for permission checks outside a view."""

    def __init__(self, user):
        self.user = user
        self.method = 'GET'
