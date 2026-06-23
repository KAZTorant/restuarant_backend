"""Core admin API views — generic CRUD backed by ModelAdmin."""

import json
from datetime import datetime

from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import FieldError, ValidationError
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.http import QueryDict
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.admin_api.pagination import AdminPagination
from apps.admin_api.permissions import IsAdminUser
from apps.admin_api.registry import build_navigation, get_model_admin
from apps.admin_api.schema import (
    build_form_schema,
    build_list_schema,
    build_model_form,
    serialize_list_row,
    serialize_object,
)


class NavigationView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({
            'user': {
                'id': request.user.pk,
                'username': request.user.username,
                'full_name': request.user.get_full_name(),
                'is_superuser': request.user.is_superuser,
                'restaurant': (
                    {'id': request.user.restaurant_id, 'name': str(request.user.restaurant)}
                    if getattr(request.user, 'restaurant_id', None)
                    else None
                ),
            },
            'apps': build_navigation(request.user),
            'site': {
                'title': 'KAZZA Admin',
                'header': 'KAZZA Panel',
            },
        })


class ModelMetaView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, app_label, model_name):
        try:
            model, model_admin = get_model_admin(app_label, model_name)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if not model_admin.has_view_permission(request):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'app_label': app_label,
            'model_name': model_name,
            'verbose_name': str(model._meta.verbose_name),
            'verbose_name_plural': str(model._meta.verbose_name_plural),
            'list': build_list_schema(model_admin, request),
            'permissions': {
                'view': model_admin.has_view_permission(request),
                'add': model_admin.has_add_permission(request),
                'change': model_admin.has_change_permission(request),
                'delete': model_admin.has_delete_permission(request),
            },
            'has_custom_list': bool(
                getattr(model_admin, 'change_list_template', None)
            ),
        })


class ModelListView(APIView):
    permission_classes = [IsAdminUser]
    pagination_class = AdminPagination

    def get(self, request, app_label, model_name):
        try:
            model, model_admin = get_model_admin(app_label, model_name)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if not model_admin.has_view_permission(request):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        qs = model_admin.get_queryset(request)
        qs = _apply_search(qs, model_admin, request)
        qs = _apply_filters(qs, model_admin, request)
        qs = _apply_date_hierarchy(qs, model_admin, request)
        qs = _apply_ordering(qs, model_admin, request)

        page_size = int(request.query_params.get('page_size', getattr(model_admin, 'list_per_page', 50)))
        page = int(request.query_params.get('page', 1))

        paginator = Paginator(qs, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages or 1)

        rows = [serialize_list_row(model_admin, request, obj) for obj in page_obj.object_list]

        return Response({
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'page': page_obj.number,
            'page_size': page_size,
            'results': rows,
        })


class ModelDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, app_label, model_name, pk):
        try:
            model, model_admin = get_model_admin(app_label, model_name)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if not model_admin.has_view_permission(request):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        qs = model_admin.get_queryset(request)
        obj = qs.filter(pk=pk).first()
        if not obj:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        schema = build_form_schema(model_admin, request, obj)
        data = serialize_object(model_admin, request, obj)

        return Response({
            'object': data,
            'schema': schema,
            'permissions': {
                'change': model_admin.has_change_permission(request, obj),
                'delete': model_admin.has_delete_permission(request, obj),
            },
        })

    def patch(self, request, app_label, model_name, pk):
        return self._save(request, app_label, model_name, pk, partial=True)

    def put(self, request, app_label, model_name, pk):
        return self._save(request, app_label, model_name, pk, partial=False)

    def delete(self, request, app_label, model_name, pk):
        try:
            model, model_admin = get_model_admin(app_label, model_name)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        qs = model_admin.get_queryset(request)
        obj = qs.filter(pk=pk).first()
        if not obj:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        if not model_admin.has_delete_permission(request, obj):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        model_admin.delete_model(request, obj)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _save(self, request, app_label, model_name, pk, partial):
        try:
            model, model_admin = get_model_admin(app_label, model_name)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        qs = model_admin.get_queryset(request)
        obj = qs.filter(pk=pk).first()
        if not obj:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        if not model_admin.has_change_permission(request, obj):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        form_data = _to_form_data(request.data)
        form = build_model_form(model_admin, request, data=form_data, obj=obj)

        if not form.is_valid():
            return Response({'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

        model_admin.save_model(request, form.instance, form, change=True)
        form.save_m2m()
        _save_inlines(request, model_admin, form.instance)

        return Response(serialize_object(model_admin, request, form.instance))


class ModelCreateView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, app_label, model_name):
        try:
            model, model_admin = get_model_admin(app_label, model_name)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if not model_admin.has_add_permission(request):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        schema = build_form_schema(model_admin, request, None)
        return Response({'schema': schema})

    def post(self, request, app_label, model_name):
        try:
            model, model_admin = get_model_admin(app_label, model_name)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if not model_admin.has_add_permission(request):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        form_data = _to_form_data(request.data)
        form = build_model_form(model_admin, request, data=form_data, obj=None)

        if not form.is_valid():
            return Response({'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

        model_admin.save_model(request, form.instance, form, change=False)
        form.save_m2m()
        _save_inlines(request, model_admin, form.instance)

        return Response(
            serialize_object(model_admin, request, form.instance),
            status=status.HTTP_201_CREATED,
        )


class RelatedChoicesView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, app_label, model_name):
        try:
            model, model_admin = get_model_admin(app_label, model_name)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        qs = model_admin.get_queryset(request)
        search = request.query_params.get('q', '')
        if search:
            search_fields = getattr(model_admin, 'search_fields', ()) or ('pk',)
            q = Q()
            for field in search_fields:
                q |= Q(**{f'{field}__icontains': search})
            qs = qs.filter(q)

        limit = min(int(request.query_params.get('limit', 50)), 200)
        results = [{'id': obj.pk, 'label': str(obj)} for obj in qs[:limit]]
        return Response({'results': results})


class ModelActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, app_label, model_name, action_name):
        try:
            model, model_admin = get_model_admin(app_label, model_name)
        except LookupError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        actions = model_admin.get_actions(request)
        if action_name not in actions:
            return Response({'detail': 'Action not found'}, status=status.HTTP_404_NOT_FOUND)

        action_func = actions[action_name]
        ids = request.data.get('ids', [])
        qs = model_admin.get_queryset(request).filter(pk__in=ids)

        if not qs.exists():
            return Response({'detail': 'No objects selected'}, status=status.HTTP_400_BAD_REQUEST)

        # Django admin actions expect (modeladmin, request, queryset)
        action_func(model_admin, request, qs)

        return Response({'detail': 'Action completed', 'count': qs.count()})


@method_decorator(ensure_csrf_cookie, name='dispatch')
class AuthLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({'detail': 'Yanlış istifadəçi adı və ya şifrə'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_staff:
            return Response({'detail': 'Admin panelinə giriş icazəsi yoxdur'}, status=status.HTTP_403_FORBIDDEN)

        login(request, user)
        return Response({
            'id': user.pk,
            'username': user.username,
            'full_name': user.get_full_name(),
            'is_superuser': user.is_superuser,
        })


class AuthLogoutView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        logout(request)
        return Response({'detail': 'Logged out'})


class AuthMeView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.pk,
            'username': user.username,
            'full_name': user.get_full_name(),
            'is_superuser': user.is_superuser,
            'restaurant': (
                {'id': user.restaurant_id, 'name': str(user.restaurant)}
                if getattr(user, 'restaurant_id', None)
                else None
            ),
        })


def _apply_search(qs, model_admin, request):
    q = request.query_params.get('q', '').strip()
    if not q:
        return qs
    search_fields = getattr(model_admin, 'search_fields', ()) or ()
    if not search_fields:
        return qs
    query = Q()
    for field in search_fields:
        query |= Q(**{f'{field}__icontains': q})
    return qs.filter(query)


def _apply_filters(qs, model_admin, request):
    for key, value in request.query_params.items():
        if not key.startswith('filter_') or not value:
            continue
        field_name = key[7:]
        try:
            qs = qs.filter(**{field_name: value})
        except (FieldError, ValueError):
            pass
    return qs


def _apply_date_hierarchy(qs, model_admin, request):
    dh = getattr(model_admin, 'date_hierarchy', None)
    if not dh:
        return qs
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    day = request.query_params.get('day')
    if year:
        qs = qs.filter(**{f'{dh}__year': year})
    if month:
        qs = qs.filter(**{f'{dh}__month': month})
    if day:
        qs = qs.filter(**{f'{dh}__day': day})
    return qs


def _apply_ordering(qs, model_admin, request):
    ordering = request.query_params.get('ordering')
    if ordering:
        return qs.order_by(*ordering.split(','))
    default = getattr(model_admin, 'ordering', None) or model_admin.model._meta.ordering
    if default:
        return qs.order_by(*default)
    return qs


def _to_form_data(data):
    if isinstance(data, QueryDict):
        return data
    qd = QueryDict(mutable=True)
    for key, value in data.items():
        if isinstance(value, list):
            for item in value:
                qd.appendlist(key, str(item))
        elif value is not None:
            qd[key] = str(value) if not isinstance(value, (dict, bool)) else json.dumps(value)
    return qd


def _save_inlines(request, model_admin, obj):
    for inline_class in model_admin.get_inlines(request, obj):
        inline = inline_class(model_admin.model, admin_site=model_admin.admin_site)
        if not inline.has_add_permission(request, obj) and not inline.has_change_permission(request, obj):
            continue
        prefix = inline.model._meta.model_name
        inlines_data = request.data.get('inlines', {}).get(prefix, [])
        if not inlines_data:
            continue
        # Inline saving is handled per-model in custom endpoints where needed
