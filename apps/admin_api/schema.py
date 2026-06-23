"""Dynamic form/list schema generation from ModelAdmin."""

from django.contrib.admin import helpers
from django.contrib.admin.utils import (
    flatten_fieldsets,
    help_text_for_field,
    label_for_field,
    lookup_field,
)
from django.db import models
from django.forms import ModelForm


def build_list_schema(model_admin, request):
    """Return changelist column definitions."""
    columns = []
    list_display = model_admin.get_list_display(request)

    for name in list_display:
        col = _column_meta(model_admin, request, name)
        if col:
            columns.append(col)

    return {
        'columns': columns,
        'list_filter': _list_filters(model_admin, request),
        'search_fields': list(getattr(model_admin, 'search_fields', ()) or ()),
        'date_hierarchy': getattr(model_admin, 'date_hierarchy', None),
        'list_per_page': getattr(model_admin, 'list_per_page', 100),
        'list_max_show_all': getattr(model_admin, 'list_max_show_all', 200),
        'ordering': _default_ordering(model_admin),
        'actions': _actions(model_admin, request),
        'show_full_result_count': getattr(model_admin, 'show_full_result_count', True),
    }


def build_form_schema(model_admin, request, obj=None):
    """Return add/change form field definitions."""
    readonly = set(model_admin.get_readonly_fields(request, obj))
    exclude = set(getattr(model_admin, 'exclude', ()) or ())
    fieldsets = model_admin.get_fieldsets(request, obj)
    flat_fields = flatten_fieldsets(fieldsets)

    form = None
    try:
        form = build_model_form(model_admin, request, obj=obj)
    except Exception:
        form = None

    fields = []
    for name in flat_fields:
        if name in exclude:
            continue
        field_meta = _field_meta(model_admin, request, name, obj, readonly, form=form)
        if field_meta:
            fields.append(field_meta)

    field_names = {f['name'] for f in fields}
    fieldset_groups = []
    for title, options in fieldsets:
        group_field_names = set(flatten_fieldsets([(title, options)]))
        group_fields = [
            name for name in group_field_names
            if name in field_names
        ]
        if group_fields:
            fieldset_groups.append({
                'title': title or '',
                'classes': list(options.get('classes', ())),
                'fields': group_fields,
            })

    if not fieldset_groups and fields:
        fieldset_groups = [{
            'title': '',
            'classes': [],
            'fields': [f['name'] for f in fields],
        }]

    inlines = []
    for inline_class in model_admin.get_inlines(request, obj):
        inline = inline_class(model_admin.model, admin_site=model_admin.admin_site)
        inline_fields = list(inline.get_fields(request, obj))
        inline_readonly = set(inline.get_readonly_fields(request, obj))
        inline_field_meta = []
        for fname in inline_fields:
            meta = _inline_field_meta(inline, request, fname, inline_readonly)
            if meta:
                inline_field_meta.append(meta)

        inlines.append({
            'model': inline.model._meta.model_name,
            'app_label': inline.model._meta.app_label,
            'verbose_name': str(inline.model._meta.verbose_name),
            'verbose_name_plural': str(inline.model._meta.verbose_name_plural),
            'fields': inline_field_meta,
            'extra': inline.extra,
            'can_add': inline.has_add_permission(request, obj),
            'can_change': inline.has_change_permission(request, obj),
            'can_delete': inline.has_delete_permission(request, obj),
            'fk_name': inline.fk_name,
        })

    filter_horizontal = list(getattr(model_admin, 'filter_horizontal', ()) or ())

    return {
        'fields': fields,
        'fieldsets': fieldset_groups,
        'inlines': inlines,
        'filter_horizontal': filter_horizontal,
        'readonly_fields': list(readonly),
    }


def build_model_form(model_admin, request, data=None, obj=None):
    """Build and return a ModelForm using admin's form machinery."""
    change = obj is not None
    form_class = model_admin.get_form(request, obj=obj, change=change)
    if data is not None:
        return form_class(data, instance=obj, files=request.FILES if hasattr(request, 'FILES') else None)
    return form_class(instance=obj)


def serialize_object(model_admin, request, obj):
    """Serialize a model instance for API response."""
    data = {'id': obj.pk}
    schema = build_form_schema(model_admin, request, obj)

    for field in schema['fields']:
        name = field['name']
        if field['type'] == 'computed':
            value = _computed_value(model_admin, request, obj, name)
        else:
            value = _field_value(obj, name, field)
        data[name] = value

    return data


def serialize_list_row(model_admin, request, obj):
    """Serialize one changelist row."""
    row = {'id': obj.pk}
    schema = build_list_schema(model_admin, request)

    for col in schema['columns']:
        name = col['name']
        if col.get('type') == 'computed':
            value = _computed_value(model_admin, request, obj, name)
        else:
            try:
                _, value = lookup_field(name, obj, model_admin)
            except Exception:
                value = getattr(obj, name, None)
        row[name] = _serialize_display_value(value)

    return row


def _column_meta(model_admin, request, name):
    try:
        label = label_for_field(name, model_admin.model, model_admin)
    except Exception:
        label = name.replace('_', ' ').title()

    is_computed = callable(getattr(model_admin, name, None)) or hasattr(
        getattr(model_admin, name, None), 'short_description'
    )

    return {
        'name': name,
        'label': str(label),
        'type': 'computed' if is_computed else 'field',
        'sortable': not is_computed and hasattr(model_admin.model, name),
    }


def _field_meta(model_admin, request, name, obj, readonly, form=None):
    if name in readonly:
        field_type = 'computed' if _is_admin_computed(model_admin, name) else 'readonly'
        return {
            'name': name,
            'label': _field_label(model_admin, name),
            'type': field_type,
            'required': False,
            'help_text': '',
            'choices': [],
            'related_model': None,
        }

    if form is None:
        try:
            form = build_model_form(model_admin, request, obj=obj)
        except Exception:
            form = None

    form_field = form.fields.get(name) if form else None

    if form_field is None:
        if hasattr(model_admin, name) and callable(getattr(model_admin, name)):
            return {
                'name': name,
                'label': _field_label(model_admin, name),
                'type': 'computed',
                'required': False,
                'help_text': '',
                'choices': [],
                'related_model': None,
            }
        return None

    field_type = _form_field_type(form_field)
    related = None
    if field_type in ('foreign_key', 'many_to_many'):
        try:
            related = {
                'app_label': form_field.queryset.model._meta.app_label,
                'model_name': form_field.queryset.model._meta.model_name,
            }
        except Exception:
            related = None

    choices = _static_field_choices(form_field, field_type)

    return {
        'name': name,
        'label': str(form_field.label or _field_label(model_admin, name)),
        'type': field_type,
        'required': form_field.required,
        'help_text': str(form_field.help_text or ''),
        'choices': choices,
        'related_model': related,
        'widget': _widget_hint(form_field),
    }


def _inline_field_meta(inline, request, name, readonly):
    if name in readonly:
        return {'name': name, 'label': name, 'type': 'readonly', 'required': False}
    try:
        form_class = inline.form or ModelForm
        # Build a dummy form to inspect fields
        from django.forms.models import modelform_factory
        Form = modelform_factory(inline.model, fields=[name] if name != inline.fk_name else inline.get_fields(request))
        form_field = Form().fields.get(name)
    except Exception:
        form_field = None

    if form_field is None:
        return {'name': name, 'label': name, 'type': 'readonly', 'required': False}

    return {
        'name': name,
        'label': str(form_field.label or name),
        'type': _form_field_type(form_field),
        'required': form_field.required,
    }


def _form_field_type(form_field):
    from django import forms
    from django.contrib.admin.widgets import FilteredSelectMultiple

    widget = form_field.widget
    if isinstance(widget, forms.PasswordInput):
        return 'password'
    if isinstance(widget, FilteredSelectMultiple):
        return 'many_to_many'
    if isinstance(form_field, forms.ModelChoiceField):
        return 'foreign_key'
    if isinstance(form_field, forms.ModelMultipleChoiceField):
        return 'many_to_many'
    if isinstance(form_field, forms.BooleanField):
        return 'boolean'
    if isinstance(form_field, forms.DateTimeField):
        return 'datetime'
    if isinstance(form_field, forms.DateField):
        return 'date'
    if isinstance(form_field, forms.TimeField):
        return 'time'
    if isinstance(form_field, (forms.DecimalField, forms.FloatField)):
        return 'decimal'
    if isinstance(form_field, forms.IntegerField):
        return 'integer'
    if isinstance(form_field, forms.FileField):
        return 'file'
    if isinstance(form_field, forms.ImageField):
        return 'image'
    if isinstance(form_field, forms.JSONField):
        return 'json'
    if isinstance(form_field, forms.CharField) and isinstance(widget, forms.Textarea):
        return 'text'
    return 'string'


def _widget_hint(form_field):
    from django import forms
    if isinstance(form_field.widget, forms.PasswordInput):
        return 'password'
    if isinstance(form_field.widget, forms.Textarea):
        return 'textarea'
    if isinstance(form_field.widget, forms.Select):
        return 'select'
    if isinstance(form_field.widget, forms.CheckboxInput):
        return 'checkbox'
    if isinstance(form_field.widget, forms.PasswordInput):
        return 'password'
    return 'input'


def _field_label(model_admin, name):
    try:
        return str(label_for_field(name, model_admin.model, model_admin))
    except Exception:
        return name.replace('_', ' ').title()


def _is_admin_computed(model_admin, name):
    method = getattr(model_admin, name, None)
    return method is not None and callable(method)


def _static_field_choices(form_field, field_type):
    """Only serialize small static choice lists; FK/M2M use the choices API."""
    if field_type in ('foreign_key', 'many_to_many'):
        return []

    try:
        if not hasattr(form_field, 'choices') or not form_field.choices:
            return []
        return [
            {'value': str(v) if v is not None else '', 'label': str(l)}
            for v, l in form_field.choices
            if v != ''
        ]
    except Exception:
        return []


def _serialize_scalar(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if isinstance(value, dict):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize_scalar(item) for item in value]
    return str(value)


def _field_value(obj, name, field_meta):
    try:
        val = getattr(obj, name)
    except Exception:
        return None

    if field_meta['type'] == 'foreign_key':
        return {'id': val.pk, 'label': str(val)} if val else None
    if field_meta['type'] == 'many_to_many':
        return [{'id': o.pk, 'label': str(o)} for o in val.all()]
    if field_meta['type'] == 'boolean':
        return bool(val)
    return _serialize_scalar(val)


def _computed_value(model_admin, request, obj, name):
    method = getattr(model_admin, name, None)
    if method and callable(method):
        try:
            result = method(obj)
            return _serialize_display_value(result)
        except Exception:
            return None
    return None


def _serialize_display_value(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _list_filters(model_admin, request):
    filters = []
    for f in model_admin.get_list_filter(request):
        if isinstance(f, str):
            filters.append({'name': f, 'type': 'choice', 'label': f.replace('_', ' ').title()})
        elif isinstance(f, (list, tuple)) and len(f) >= 2:
            filters.append({'name': f[0], 'type': 'choice', 'label': str(f[1])})
        else:
            filters.append({'name': str(f), 'type': 'custom', 'label': str(f)})
    return filters


def _actions(model_admin, request):
    actions = []
    for name, func in model_admin.get_actions(request).items():
        if name == 'delete_selected':
            continue
        actions.append({
            'name': name,
            'label': str(getattr(func, 'short_description', name)),
        })
    return actions


def _default_ordering(model_admin):
    ordering = getattr(model_admin, 'ordering', None) or model_admin.model._meta.ordering
    return list(ordering or ('-pk',))
