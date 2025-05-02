from django.contrib import admin
from django.utils.html import format_html
from django.contrib.admin.views.main import ChangeList
from simple_history.utils import get_history_model_for_model
from datetime import timedelta

from apps.orders.models import Order, OrderItem

# Grab the generated history models
HistoricalOrder = get_history_model_for_model(Order)
HistoricalOrderItem = get_history_model_for_model(OrderItem)

# Friendly names in the admin
HistoricalOrder._meta.verbose_name = 'Arxiv (Sifariş)'
HistoricalOrder._meta.verbose_name_plural = 'Arxiv (Sifarişlər) 🎞️'
HistoricalOrderItem._meta.verbose_name = 'Arxiv (Sifariş məhsulu)'
HistoricalOrderItem._meta.verbose_name_plural = 'Arxiv (Sifariş məhsulu) 🎞️'


# Paginate: one history record per page
class SingleItemChangeList(ChangeList):
    def get_results(self, *args, **kwargs):
        super().get_results(*args, **kwargs)
        cnt = len(self.result_list)
        self.result_count = self.full_result_count = cnt
        self.paginator._count = cnt
        self.paginator.per_page = 1


@admin.register(HistoricalOrder)
class HistoricalOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'table',
        'is_paid',
        'waitress',
        'total_price',
        'history_type',
        'created_at',
        'get_history_reason',
    ]
    list_filter = ['id', 'waitress', 'table']

    def get_changelist(self, request, **kwargs):
        return SingleItemChangeList

    def get_history_reason(self, obj):
        # ORDER-LEVEL creates/deletes
        if obj.history_type == '+':
            return format_html("<ul><li>Yeni sifariş yaradıldı</li></ul>")
        if obj.history_type == '-':
            return format_html("<ul><li>Sifariş silindi</li></ul>")

        # Determine time window: (prev_date, this_date]
        prev = obj.prev_record
        start = prev.history_date if prev else obj.history_date - \
            timedelta(seconds=1)
        end = obj.history_date

        # All item-history for this order in that window
        related = HistoricalOrderItem.objects.filter(
            order_id=obj.id,
            history_date__gt=start,
            history_date__lte=end
        ).order_by('history_date', 'history_id')

        # Group and count
        adds, removes = {}, {}
        changes = {}  # key=(meal, field, old, new) -> count

        for item in related:
            meal = str(item.meal) if item.meal else "—"
            qty = item.quantity

            if item.history_type == '+':
                adds[meal] = adds.get(meal, 0) + qty

            elif item.history_type == '-':
                removes[meal] = removes.get(meal, 0) + qty

            elif item.history_type == '~' and item.prev_record:
                prev_item = item.prev_record
                for field in item.instance._meta.fields:
                    name = field.name
                    try:
                        old = getattr(prev_item, name, None)
                        new = getattr(item, name, None)
                    except Exception:
                        continue
                    if old != new:
                        key = (meal, name, old, new)
                        changes[key] = changes.get(key, 0) + 1

        # Build list items
        lines = []
        for meal, total in adds.items():
            lines.append(f"Əlavə edildi: {meal} ({total})")
        for meal, total in removes.items():
            lines.append(f"Silindi: {meal} ({total})")
        for (meal, name, old, new), cnt in changes.items():
            lines.append(f"Dəyişdi: {meal} — {name}: {old} → {new} ({cnt})")

        if not lines:
            lines = ["Dəyişiklik tapılmadı"]

        # Render each as a bullet
        html = "<ul>"
        for l in lines:
            html += f"<li>{l}</li>"
        html += "</ul>"
        return format_html(html)

    get_history_reason.short_description = "Dəyişiklik Səbəbi"
