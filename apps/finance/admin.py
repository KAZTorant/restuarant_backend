from django.contrib import admin

from apps.finance.models import Expense, Income
from apps.tenants.mixins import TenantAdminMixin


@admin.register(Income)
class IncomeAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('payment_type', 'amount', 'date', 'restaurant')
    list_filter = ('payment_type', 'date')


@admin.register(Expense)
class ExpenseAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('category', 'amount', 'date', 'restaurant')
    list_filter = ('category', 'date')
