from django.contrib import admin
from apps.orders.models import WorkPeriodConfig, Report


@admin.register(WorkPeriodConfig)
class WorkPeriodConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time',
                    'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    ordering = ('-created_at',)

    fieldsets = (
        ('Əsas Məlumatlar', {
            'fields': ('name', 'start_time', 'end_time', 'is_active')
        }),
        ('Tarixlər', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('work_period_config', 'start_datetime', 'end_datetime',
                    'total_amount', 'cash_total', 'card_total', 'other_total', 'unpaid_total')
    list_filter = ('work_period_config', 'start_datetime', 'created_at')
    search_fields = ('work_period_config__name',)
    ordering = ('-start_datetime',)

    fieldsets = (
        ('Dövrü Məlumatları', {
            'fields': ('work_period_config', 'start_datetime', 'end_datetime')
        }),
        ('Maliyyə Məlumatları', {
            'fields': ('total_amount', 'cash_total', 'card_total', 'other_total', 'unpaid_total')
        }),
        ('Sifarişlər', {
            'fields': ('orders',),
            'classes': ('collapse',)
        }),
        ('Tarixlər', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'total_amount',
                       'cash_total', 'card_total', 'other_total', 'unpaid_total')
    filter_horizontal = ('orders',)

    def get_readonly_fields(self, request, obj=None):
        # Make financial fields read-only since they're calculated automatically
        readonly = list(self.readonly_fields)
        if obj:  # editing an existing object
            readonly.extend(
                ['work_period_config', 'start_datetime', 'end_datetime'])
        return readonly
