from django.contrib import admin
from django.utils.html import format_html
from django.contrib.admin.views.main import ChangeList
from simple_history.utils import get_history_model_for_model
from datetime import timedelta, datetime

from apps.orders.models import Order, OrderItem

HistoricalOrder = get_history_model_for_model(Order)
HistoricalOrderItem = get_history_model_for_model(OrderItem)

HistoricalOrder._meta.verbose_name = 'Arxiv (Sifariş)'
HistoricalOrder._meta.verbose_name_plural = 'Arxiv (Sifarişlər) 🎞️'
HistoricalOrderItem._meta.verbose_name = 'Arxiv (Sifariş məhsulu)'
HistoricalOrderItem._meta.verbose_name_plural = 'Arxiv (Sifariş məhsulu) 🎞️'


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
        'id', 'table', 'is_paid', 'waitress',
        'total_price', 'history_type', 'created_at',
        'get_history_reason',
    ]
    list_filter = ['id', 'waitress', 'table']

    def get_changelist(self, request, **kwargs):
        return SingleItemChangeList

    def get_history_reason(self, obj):
        lines = []

        # 1) Order‐level creation/deletion
        if obj.history_type == '+':
            return format_html("<ul><li>Yeni sifariş yaradıldı</li></ul>")
        if obj.history_type == '-':
            return format_html("<ul><li>Sifariş silindi</li></ul>")

        # 2) Order‐level field-diffs (including upgraded updated_at)
        prev = obj.prev_record
        if prev:
            for fld in obj.instance._meta.fields:
                name = fld.name
                # skip non‐business fields
                if name in ('id', 'history_id', 'history_date', 'history_user', 'created_at'):
                    continue

                old = getattr(prev, name, None)
                new = getattr(obj,  name, None)
                if old == new:
                    continue

                # special case for updated_at → show elapsed time
                if name == 'updated_at' and isinstance(old, datetime) and isinstance(new, datetime):
                    delta = new - old
                    secs = delta.total_seconds()
                    if secs < 1:
                        label = f"{int(delta.microseconds/1000)} ms"
                    elif secs < 60:
                        label = f"{secs:.1f} s"
                    else:
                        mins = int(secs // 60)
                        sec = int(secs % 60)
                        label = f"{mins} m {sec} s"
                    lines.append(f"Yeniləmə müddəti: {label}")
                    continue

                # other datetime fields: pretty format
                if isinstance(old, datetime) and isinstance(new, datetime):
                    old_str = old.strftime('%d %b %Y, %H:%M:%S')
                    new_str = new.strftime('%d %b %Y, %H:%M:%S')
                    lines.append(
                        f"{fld.verbose_name or name}: {old_str} → {new_str}")
                else:
                    lines.append(f"{fld.verbose_name or name}: {old} → {new}")

        # 3) OrderItem‐level incremental changes
        start = prev.history_date if prev else obj.history_date - \
            timedelta(seconds=1)
        end = obj.history_date
        items = HistoricalOrderItem.objects.filter(
            order_id=obj.id,
            history_date__gt=start,
            history_date__lte=end
        )

        adds, removes = {}, {}
        changes = {}  # (meal, field, old, new) → count

        for it in items:
            meal = str(it.meal) if it.meal else "—"
            qty = it.quantity

            if it.history_type == '+':
                adds[meal] = adds.get(meal, 0) + qty
            elif it.history_type == '-':
                removes[meal] = removes.get(meal, 0) + qty
            elif it.history_type == '~' and it.prev_record:
                prev_it = it.prev_record
                for fld in it.instance._meta.fields:
                    nm = fld.name
                    o = getattr(prev_it, nm, None)
                    n = getattr(it,      nm, None)
                    if o != n:
                        key = (meal, nm, o, n)
                        changes[key] = changes.get(key, 0) + 1

        for meal, tot in adds.items():
            lines.append(f"Əlavə edildi: {meal} ({tot})")
        for meal, tot in removes.items():
            lines.append(f"Silindi: {meal} ({tot})")
        for (meal, nm, o, n), cnt in changes.items():
            lines.append(f"Dəyişdi: {meal} — {nm}: {o} → {n} ({cnt})")

        if not lines:
            lines = ["Dəyişiklik tapılmadı"]

        html = "<ul>" + "".join(f"<li>{line}</li>" for line in lines) + "</ul>"
        return format_html(html)

    get_history_reason.short_description = "Dəyişiklik Səbəbi"
