from django.core.exceptions import ValidationError


def validate_unique_name(queryset, field_name, value, error_message, *, exclude_pk=None):
    if not value:
        return
    qs = queryset.filter(**{f'{field_name}__iexact': value})
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        raise ValidationError({field_name: error_message})
