from django.contrib import admin
from django.utils.html import format_html
from django.contrib.admin.views.main import ChangeList
from simple_history.utils import get_history_model_for_model
from datetime import timedelta, datetime

from apps.orders.models import Order, OrderItem

# Retrieve the generated history models
HistoricalOrder = get_history_model_for_model(Order)
HistoricalOrderItem = get_history_model_for_model(OrderItem)

# Friendly names in admin
HistoricalOrder._meta.verbose_name = 'Arxiv (Sifariş)'
HistoricalOrder._meta.verbose_name_plural = 'Arxiv (Sifarişlər) 🎞️'
HistoricalOrderItem._meta.verbose_name = 'Arxiv (Sifariş məhsulu)'
HistoricalOrderItem._meta.verbose_name_plural = 'Arxiv (Sifariş məhsulu) 🎞️'


class SingleItemChangeList(ChangeList):
    """Show one history record per page."""

    def get_results(self, request, *args, **kwargs):
        super().get_results(request, *args, **kwargs)
        cnt = len(self.result_list)
        self.result_count = self.full_result_count = cnt
        self.paginator._count = cnt
        self.paginator.per_page = 1


@admin.register(HistoricalOrder)
class HistoricalOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'table', 'is_paid', 'waitress',
        'total_price', 'history_type', 'history_date',
        'get_history_reason',
    ]
    list_filter = ['id', 'waitress', 'table']
    list_per_page = 20

    def get_changelist(self, request, **kwargs):
        return SingleItemChangeList

    def get_history_reason(self, obj):
        # Creation or deletion
        if obj.history_type == '+':
            return format_html("<ul><li>Yeni sifariş yaradıldı</li></ul>")
        if obj.history_type == '-':
            return format_html("<ul><li>Sifariş silindi</li></ul>")

        lines = []
        lines += self._get_order_field_changes(obj)
        lines += self._get_item_level_changes(obj)

        if not lines:
            lines = ["Dəyişiklik tapılmadı"]

        return format_html(self._wrap_as_list(lines))

    get_history_reason.short_description = "Dəyişiklik Səbəbi"

    def _get_order_field_changes(self, obj):
        """Detect changes on the Order itself; elapsed for any datetime field."""
        prev = obj.prev_record
        if not prev:
            return []

        changes = []
        for fld in obj.instance._meta.fields:
            name = fld.name
            if name in ('id', 'history_id', 'history_date', 'history_user', 'created_at'):
                continue

            old, new = getattr(prev, name), getattr(obj, name)
            if old == new:
                continue

            # Any datetime → elapsed
            if isinstance(old, datetime) and isinstance(new, datetime):
                elapsed = self._format_elapsed(old, new)
                changes.append(f"{fld.verbose_name}: {elapsed}")
            # Booleans → Bəli/Xeyr
            elif isinstance(old, bool) and isinstance(new, bool):
                old_lbl = 'Bəli' if old else 'Xeyr'
                new_lbl = 'Bəli' if new else 'Xeyr'
                changes.append(f"{fld.verbose_name}: {old_lbl} → {new_lbl}")
            else:
                changes.append(f"{fld.verbose_name}: {old} → {new}")
        return changes

    def _format_elapsed(self, old, new):
        """Return human-readable elapsed time between two datetimes."""
        delta = new - old
        secs = delta.total_seconds()
        if secs < 1:
            return f"{int(delta.microseconds/1000)} ms"
        if secs < 60:
            return f"{secs:.1f} s"
        m, s = divmod(int(secs), 60)
        return f"{m} m {s} s"

    def _get_item_level_changes(self, obj):
        """
        Detect additions, removals, and field changes
        between this record and the previous, excluding
        updated_at elapsed from OrderItem level.
        """
        prev = obj.prev_record
        start = prev.history_date if prev else obj.history_date - \
            timedelta(seconds=1)
        end = obj.history_date
        items = HistoricalOrderItem.objects.filter(
            order_id=obj.id,
            history_date__gt=start,
            history_date__lte=end
        )

        adds, removes, updates = {}, {}, {}
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
                    if nm == 'updated_at':  # skip elapsed here
                        continue
                    old = getattr(prev_it, nm, None)
                    new = getattr(it,       nm, None)
                    if old != new:
                        key = (meal, fld.verbose_name or nm, old, new)
                        updates[key] = updates.get(key, 0) + 1

        lines = []
        for meal, tot in adds.items():
            lines.append(f"Əlavə edildi: {meal} ({tot} ədəd)")
        for meal, tot in removes.items():
            lines.append(f"Silindi: {meal} ({tot} ədəd)")
        for (meal, fname, old, new), cnt in updates.items():
            # boolean fields
            if isinstance(old, bool) and isinstance(new, bool):
                o_lbl = 'Bəli' if old else 'Xeyr'
                n_lbl = 'Bəli' if new else 'Xeyr'
                lines.append(
                    f"Dəyişdi: {meal} — {fname}: {o_lbl} → {n_lbl} ({cnt} ədəd)")
            else:
                lines.append(
                    f"Dəyişdi: {meal} — {fname}: {old} → {new} ({cnt} ədəd)")
        return lines

    def _wrap_as_list(self, lines):
        """Wrap a list of strings into an HTML <ul> list."""
        html = "<ul>"
        for line in lines:
            html += f"<li>{line}</li>"
        html += "</ul>"
        return html
