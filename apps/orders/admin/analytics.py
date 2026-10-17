from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import render

from apps.admin_api.views_analytics import sales_analytics_payload


def analytics_page(request):
    context = admin.site.each_context(request)
    context['title'] = 'Satış paneli'
    return render(request, 'admin/sales_analytics.html', context)


def analytics_data(request):
    try:
        payload = sales_analytics_payload(request.user, request.GET)
    except ValueError as exc:
        return JsonResponse({'detail': str(exc)}, status=400)
    return JsonResponse(payload)
