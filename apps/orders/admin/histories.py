from datetime import datetime, timedelta

from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import result_headers
from django.contrib.admin.views.main import ChangeList
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Count, Max
from django.utils.safestring import mark_safe
from simple_history.utils import get_history_model_for_model

from apps.orders.models import Order, OrderItem
from apps.tenants.mixins import TenantAdminMixin

ARCHIVE_VIEW_PARAM = 'archive_view'
GROUP_PAGE_PARAM = 'gp'
ARCHIVE_VIEW_DATE = 'date'
ARCHIVE_VIEW_GROUPED = 'grouped'

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

    def get_filters_params(self, params=None):
        lookup_params = super().get_filters_params(params)
        lookup_params.pop(ARCHIVE_VIEW_PARAM, None)
        lookup_params.pop(GROUP_PAGE_PARAM, None)
        return lookup_params

    def get_results(self, request, *args, **kwargs):
        super().get_results(request, *args, **kwargs)
        cnt = len(self.result_list)
        self.result_count = self.full_result_count = cnt
        self.paginator._count = cnt
        self.paginator.per_page = 1


@admin.register(HistoricalOrder)
class HistoricalOrderAdmin(TenantAdminMixin, admin.ModelAdmin):
    tenant_lookup = 'table__room__restaurant'
    show_restaurant_in_list = False
    list_display = [
        'id', 'table', 'is_paid', 'waitress',
        'total_price', 'history_type', 'history_date',
        'get_history_reason',
    ]
    list_filter = ['id', 'waitress', 'table']
    list_per_page = 20
    change_list_template = 'admin/orders/historicalorder/change_list.html'

    def get_changelist(self, request, **kwargs):
        return SingleItemChangeList

    def changelist_view(self, request, extra_context=None):
        view = request.GET.get(ARCHIVE_VIEW_PARAM, ARCHIVE_VIEW_DATE)
        if view not in (ARCHIVE_VIEW_DATE, ARCHIVE_VIEW_GROUPED):
            view = ARCHIVE_VIEW_DATE
        extra_context = extra_context or {}
        extra_context.update({
            'archive_view': view,
            'archive_date_url': self._archive_view_url(request, ARCHIVE_VIEW_DATE),
            'archive_grouped_url': self._archive_view_url(request, ARCHIVE_VIEW_GROUPED),
        })
        response = super().changelist_view(request, extra_context=extra_context)
        if (
            view == ARCHIVE_VIEW_GROUPED
            and getattr(response, 'context_data', None)
            and response.context_data.get('cl') is not None
        ):
            response.context_data.update(
                self._build_grouped_context(
                    request, response.context_data['cl']
                )
            )
        return response

    def _archive_view_url(self, request, view):
        params = request.GET.copy()
        params[ARCHIVE_VIEW_PARAM] = view
        params.pop('p', None)
        params.pop(GROUP_PAGE_PARAM, None)
        return '?' + params.urlencode()

    def _group_page_url(self, request, page_number):
        params = request.GET.copy()
        params[ARCHIVE_VIEW_PARAM] = ARCHIVE_VIEW_GROUPED
        params.pop('p', None)
        if page_number <= 1:
            params.pop(GROUP_PAGE_PARAM, None)
        else:
            params[GROUP_PAGE_PARAM] = str(page_number)
        return '?' + params.urlencode()

    def _group_headers(self, cl):
        headers = []
        for header in result_headers(cl):
            class_attrib = str(header.get('class_attrib') or '')
            if 'action-checkbox' in class_attrib:
                continue
            headers.append(header['text'])
        return headers

    def _build_grouped_context(self, request, cl):
        queryset = cl.queryset
        headers = self._group_headers(cl)
        annotated = (
            queryset.order_by()
            .values('id')
            .annotate(latest=Max('history_date'), event_count=Count('history_id'))
            .order_by('-latest', '-id')
        )
        paginator = Paginator(annotated, self.list_per_page)
        try:
            page_number = int(request.GET.get(GROUP_PAGE_PARAM, 1))
        except (TypeError, ValueError):
            page_number = 1
        if page_number < 1:
            page_number = 1
        if paginator.count == 0:
            return {
                'order_groups': [],
                'group_result_count': 0,
                'group_page_links': [],
                'group_has_previous': False,
                'group_has_next': False,
                'group_prev_url': '',
                'group_next_url': '',
                'group_headers': headers,
                'group_colspan': len(headers),
            }
        try:
            page = paginator.page(page_number)
        except EmptyPage:
            page = paginator.page(paginator.num_pages)

        ids = [row['id'] for row in page.object_list]
        records = queryset.filter(id__in=ids).order_by('history_date', 'history_id')
        events_by_id = {}
        for record in records:
            events_by_id.setdefault(record.id, []).append({
                'record': record,
                'reason': self.get_history_reason(record),
                'type_label': record.get_history_type_display(),
            })

        groups = []
        for row in page.object_list:
            events = events_by_id.get(row['id'], [])
            if not events:
                continue
            groups.append({
                'id': row['id'],
                'latest': events[-1]['record'],
                'event_count': len(events),
                'events': events,
            })

        links = []
        for item in paginator.get_elided_page_range(page.number):
            if isinstance(item, int):
                links.append({
                    'number': item,
                    'url': self._group_page_url(request, item),
                    'current': item == page.number,
                    'ellipsis': False,
                })
            else:
                links.append({
                    'ellipsis': True,
                    'number': '',
                    'url': '',
                    'current': False,
                })

        return {
            'order_groups': groups,
            'group_result_count': paginator.count,
            'group_page_links': links,
            'group_has_previous': page.has_previous(),
            'group_has_next': page.has_next(),
            'group_prev_url': (
                self._group_page_url(request, page.previous_page_number())
                if page.has_previous() else ''
            ),
            'group_next_url': (
                self._group_page_url(request, page.next_page_number())
                if page.has_next() else ''
            ),
            'group_headers': headers,
            'group_colspan': len(headers),
        }

    def get_history_reason(self, obj):
        # Creation or deletion
        if obj.history_type == '+':
            return mark_safe("<ul><li>Yeni sifariş yaradıldı</li></ul>")
        if obj.history_type == '-':
            return mark_safe("<ul><li>Sifariş silindi</li></ul>")

        lines = []
        lines += self._get_order_field_changes(obj)
        lines += self._get_item_level_changes(obj)

        if not lines:
            lines = ["Dəyişiklik tapılmadı"]

        return mark_safe(self._wrap_as_list(lines))

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
        return html
