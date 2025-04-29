from django.contrib import admin, messages
from django.forms import ValidationError
from django.urls import path
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.utils.dateformat import format
from django.utils.timezone import localtime
from django.db.models import Min
from django.db.models import Max
from django.db.models import Sum
from django.utils.html import format_html

from decimal import Decimal

from simple_history.admin import SimpleHistoryAdmin

from apps.orders.models import Statistics, Order

from apps.orders.models.order import OrderItem
from apps.payments.models.pay_table_orders import Payment
from apps.printers.utils.service import PrinterService
from apps.printers.utils.service_v2 import PrinterService as PrinterServiceV2


class OrderInline(admin.TabularInline):
    """
    Inline admin to display Orders associated with a Statistics (shift) record.
    """
    model = Statistics.orders.through
    extra = 0
    can_delete = False
    show_change_link = False
    fields = ('pk', 'table', 'total_price', 'is_paid', 'created_at')
    readonly_fields = fields

    def pk(self, obj):
        return obj.order.id

    def table(self, obj):
        return obj.order.table

    def total_price(self, obj):
        return obj.order.total_price

    def is_paid(self, obj):
        return obj.order.is_paid
    is_paid.boolean = True

    def created_at(self, obj):
        return format(localtime(obj.order.created_at), 'Y-m-d H:i:s')

    pk.short_description = 'ID'
    table.short_description = 'Stol'
    total_price.short_description = 'Məbləğ'
    is_paid.short_description = 'Ödənilib'
    created_at.short_description = 'Yaradılma Tarixi'

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return False


@admin.register(Statistics)
class StatisticsAdmin(SimpleHistoryAdmin):
    """
    Admin for shift-based Statistics with both historical Z-check and shift start/end.
    """
    list_display = (
        'started_by', 'start_time',
        'total', 'remaining_cash',
        'end_time', 'is_closed')
    list_filter = ('title', 'date', 'waitress_info', 'is_closed', 'started_by')
    exclude = ('orders',)
    change_list_template = 'admin/statistics_change_list.html'
    readonly_fields = [
        'title', 'total', 'date', 'waitress_info', 'is_z_checked',
        'started_by', 'start_time', 'initial_cash',
        'ended_by', 'end_time', 'is_closed',
        'initial_cash', 'cash_total', 'card_total', 'other_total',
        'withdrawn_amount', 'remaining_cash', 'notes',
        'display_per_waitress', 'display_order_items',


    ]

    fieldsets = (
        ('🔎 Ümumi Məlumat', {
            'fields': ('title', 'total', 'date', 'is_z_checked'),
        }),
        ('💰 Məbləğlər', {
            'classes': ('collapse',),
            'fields': (
                'initial_cash', 'cash_total', 'card_total',
                'other_total', 'withdrawn_amount',
                'remaining_cash'
            ),
        }),
        ('⏱️ Növbə Detalları', {
            'fields': (
                'started_by', 'start_time',
                'ended_by', 'end_time', 'is_closed'
            ),
        }),
        ('📝 Qeydlər və Hesabatlar', {
            'classes': ('collapse',),
            'fields': (
                'notes',
                'display_per_waitress',
                'display_order_items',
            ),
        }),
    )
    inlines = [OrderInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(started_by=request.user)

    def has_add_permission(self, request):
        # Creation only via Start Shift action
        return False

    def has_change_permission(self, request, obj=None):
        # Only allow editing an open shift by its starter
        if obj and (obj.started_by != request.user):
            return False
        return super().has_change_permission(request, obj)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('calculate-till-now/', self.admin_site.admin_view(self.calculate_till_now),
                 name='orders_statistics_calculate_till_now'),
            path('calculate-daily/', self.admin_site.admin_view(self.calculate_daily_stats),
                 name='orders_statistics_calculate_daily'),
            path('calculate-monthly/', self.admin_site.admin_view(self.calculate_monthly_stats),
                 name='orders_statistics_calculate_monthly'),
            path('calculate-yearly/', self.admin_site.admin_view(self.calculate_yearly_stats),
                 name='orders_statistics_calculate_yearly'),
            path('calculate-per-waitress/', self.admin_site.admin_view(
                self.calculate_per_waitress_stats), name='orders_statistics_calculate_per_waitress'),
            path('active-orders/', self.admin_site.admin_view(self.active_orders),
                 name='orders_statistics_active_orders'),
            # Shift actions
            path(
                'current-shift-info/',
                self.admin_site.admin_view(self.current_shift_info),
                name='orders_statistics_current_shift_info'
            ),

            path(
                'start-shift-info/',
                self.admin_site.admin_view(self.start_shift_info),
                name='orders_statistics_start_shift_info'
            ),
            path('start-shift/', self.admin_site.admin_view(self.start_shift_view),
                 name='orders_statistics_start_shift'),
            path('<int:shift_id>/end-shift/', self.admin_site.admin_view(
                self.end_shift_view), name='orders_statistics_end_shift'),
            path('<int:shift_id>/print-shift-summary/', self.admin_site.admin_view(
                self.print_shift_summary), name='orders_statistics_print_shift_summary'),
        ]
        return custom + urls

    # === Existing calculation endpoints ===
    def calculate_per_waitress_stats(self, request):
        Statistics.objects.calculate_per_waitress()
        self.message_user(
            request, "Ofisiant statistikası uğurla əlavə edildi.")
        return HttpResponseRedirect('..')

    def calculate_daily_stats(self, request):
        Statistics.objects.calculate_daily()
        self.message_user(request, "Günlük statistika uğurla əlavə edildi.")
        return HttpResponseRedirect('..')

    def calculate_monthly_stats(self, request):
        Statistics.objects.calculate_monthly()
        self.message_user(request, "Aylıq statistika uğurla əlavə edildi.")
        return HttpResponseRedirect('..')

    def calculate_yearly_stats(self, request):
        Statistics.objects.calculate_yearly()
        self.message_user(request, "İllik statistika uğurla əlavə edildi.")
        return HttpResponseRedirect('..')

    def calculate_till_now(self, request):
        Statistics.objects.calculate_till_now(request.user)
        self.message_user(
            request, "Bu günə kimi olan statistika uğurla əlavə edildi.")
        return HttpResponseRedirect('..')

    # === Z-check endpoints ===
    def z_check(self, obj):
        Statistics.objects.delete_orders_for_statistics_day(obj.date)
        try:
            PrinterService().send_to_printer(data=obj.print_check)
        except Exception:
            return False
        return True

    def z_check_till_now(self, obj):
        obj.delete_orders_till_now()
        try:
            PrinterService().send_to_printer(data=obj.print_check)
        except Exception:
            return False
        return True

    def response_change(self, request, obj):
        # Legacy Z-check buttons
        if '_print_z_receipt' in request.POST:
            success, msg = PrinterServiceV2.print_z_hesabat(
                stat_id=obj.pk, user=request.user
            )
            level = messages.SUCCESS if success else messages.ERROR
            self.message_user(request, msg, level=level)
            return HttpResponseRedirect('.')

        if '_print_shift_summary' in request.POST:
            success, msg = PrinterServiceV2.print_shift_summary(
                stat_id=obj.pk, user=request.user)
            level = messages.SUCCESS if success else messages.ERROR
            self.message_user(request, msg, level=level)
            return HttpResponseRedirect('.')

        if '_end_shift' in request.POST:
            try:
                # if you have a withdrawn_amount field in the form, grab it here:
                withdrawn = Decimal(request.POST.get(
                    'withdrawn_amount', '0') or '0')
                Statistics.objects.calculate_till_now()
                Statistics.objects.end_shift(obj, request.user, withdrawn)
                self.message_user(request,
                                  (
                                      "Növbə uğurla bağlandı."
                                      " Qalan nağd: %s AZN"
                                  ) % obj.remaining_cash,
                                  messages.SUCCESS
                                  )
            except ValidationError as e:
                self.message_user(request, str(e), messages.ERROR)
            return HttpResponseRedirect('.')

        # Refresh (recalculate till_now) button
        if '_refresh' in request.POST:
            Statistics.objects.calculate_till_now(request.user)
            self.message_user(request, "Statistika yeniləndi.")
            return HttpResponseRedirect('.')

        return super().response_change(request, obj)

    # === Active orders JSON ===
    def active_orders(self, request):
        paid = Order.objects.filter(is_paid=True).aggregate(
            sum=Sum('total_price'))['sum'] or 0
        unpaid = Order.objects.filter(is_paid=False).aggregate(
            sum=Sum('total_price'))['sum'] or 0
        return JsonResponse({'total_paid': paid, 'total_unpaid': unpaid})

    # === Shift-specific actions ===

    def current_shift_info(self, request):
        Statistics.objects.calculate_till_now(request.user)

        shift = Statistics.objects.filter(
            started_by=request.user,
            is_closed=False
        ).first()
        if not shift:
            raise Http404()

        return JsonResponse({
            'shift_id':    shift.id,
            'cash_total':  str(shift.cash_total),
            'card_total':  str(shift.card_total),
            'other_total': str(shift.other_total),
            'total': str(shift.total),
            'cash_in_hand': str(shift.cash_total + shift.initial_cash),
            'initial_cash': str(shift.initial_cash),
        })

    def start_shift_info(self, request):
        Statistics.objects.calculate_till_now(request.user)

        last = Statistics.objects.filter(
            is_closed=True
        ).order_by('-end_time').first()
        if not last:
            JsonResponse({'initial_cash': str(0)})
        initial = last.remaining_cash if last else Decimal('0.00')
        return JsonResponse({'initial_cash': str(initial)})

    def start_shift_view(self, request):
        if request.method == 'POST':
            try:
                init_cash = Decimal(request.POST.get(
                    'initial_cash', '0') or '0')
                notes = request.POST.get('notes', '').strip()

                shift = Statistics.objects.start_shift(request.user)
                shift.initial_cash = init_cash
                shift.notes = notes
                shift.save()

                Statistics.objects.calculate_till_now(request.user)

                self.message_user(
                    request,
                    f"Növbə açıldı(Başlanğıc nağd: {shift.initial_cash} AZN)",
                    level=messages.SUCCESS
                )
            except ValidationError as e:
                self.message_user(request, str(e), level=messages.ERROR)
        return HttpResponseRedirect('..')

    def end_shift_view(self, request, shift_id):
        shift = self.get_object(request, shift_id)
        withdrawn = Decimal(request.POST.get('withdrawn_amount', '0') or '0')
        try:
            shift = Statistics.objects.end_shift(
                shift, request.user, withdrawn)
            self.message_user(
                request, f"Shift ended. Remaining cash: {shift.remaining_cash}")
        except ValidationError as e:
            self.message_user(request, e.message, level=messages.ERROR)
        return HttpResponseRedirect('../..')

    def print_shift_summary(self, request, shift_id):
        obj = self.get_object(request, shift_id)
        PrinterServiceV2.print_shift_summary(stat_id=obj.pk, user=request.user)
        self.message_user(request, "Shift summary sent to printer.")
        return HttpResponseRedirect('../..')

    title_with_date = SimpleHistoryAdmin.date_hierarchy

    def display_per_waitress(self, obj):
        # Get all orders related to this statistic
        orders = Order.objects.all_orders().filter(statistics=obj)

        # Get the oldest and latest created_at dates
        order_dates = orders.aggregate(
            oldest_order=Min('created_at'),
            latest_order=Max('created_at')
        )

        oldest_order = order_dates['oldest_order']
        latest_order = order_dates['latest_order']

        # Group by waitress and sum the total_price
        waitress_totals = orders.values('waitress__first_name', 'waitress__last_name').annotate(
            total_served=Sum('total_price')
        )
        return self.create_table_for_per_waitress(waitress_totals, oldest_order, latest_order)

    def display_order_items(self, obj):
        # Get all orders related to this statistic
        orders = Order.objects.all_orders().filter(statistics=obj)

        # Get the oldest and latest created_at dates
        order_dates = orders.aggregate(
            oldest_order=Min('created_at'),
            latest_order=Max('created_at')
        )

        oldest_order = order_dates['oldest_order']
        latest_order = order_dates['latest_order']

        # Get all order items related to these orders
        order_items = OrderItem.objects.all_order_items().filter(order__in=orders)
        order_items = order_items.values('meal__name').annotate(
            total_quantity=Sum('quantity')
        ).annotate(total_price=Sum('price'))

        if not order_items.exists():
            return "No orders found."
        return self.create_table_for_order_items(order_items, oldest_order, latest_order)

    def create_table_for_per_waitress(self, waitress_totals, oldest_order, latest_order):
        # Format dates to include time (hours and minutes)
        oldest_order_str = oldest_order.strftime('%d %B %Y, %H:%M')
        latest_order_str = latest_order.strftime('%d %B %Y, %H:%M')

        # Styled help text
        help_text_html = f"""
        <small style="display: block; font-size: 0.9rem; color: #666; margin-bottom: 10px;">
            <span> Hər ofisiantın xidmət etdiyi sifarişlərin cəm məbləğidir.
            <br>
            *<span style="font-weight: bold;">{oldest_order_str}</span> tarixdən <span style="font-weight: bold;">{latest_order_str}</span> tarixədək</span>
        </small>
        """

        # Start building the table
        table_html = """
        <hr>
        <table class='table table-striped' style="border-collapse: collapse; width: 100%; margin-top: 20px; box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);">
            <caption style="caption-side: top; text-align: center; font-weight: bold; font-size: 1.5rem; padding-bottom: 8px; color: #444;">
                Ofisiantların xidməti
            </caption>
            <thead style="background-color: #f2f2f2;">
                <tr>
                    <th style="padding: 10px; border-bottom: 1px solid #ddd;">#</th>
                    <th style="padding: 10px; border-bottom: 1px solid #ddd;">Ofisiant</th>
                    <th style="padding: 10px; border-bottom: 1px solid #ddd;">Ümumi Məbləğ</th>
                </tr>
            </thead>
            <tbody>
        """
        total_server_by_waitresses = 0
        # Iterate through each waitress and display their total served amount
        for index, waitress in enumerate(waitress_totals, start=1):
            waitress_name = f"{waitress['waitress__first_name']} {waitress['waitress__last_name']}" or "Məlum deyil"
            total_served = waitress['total_served'] or 0
            total_server_by_waitresses += float(total_served)
            table_html += f"""
                <tr style="background-color: {'#ffffff' if index % 2 == 0 else '#f9f9f9'};">
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{index}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{waitress_name}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{total_served} (AZN)</td>
                </tr>
            """
        # Adding total row at the end
        table_html += f"""
            <tr style="font-weight: bold; background-color: #e6e6e6;">
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Cəmi</td>
                <td></td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{total_server_by_waitresses} (AZN)</td>
            </tr>
        """

        table_html += "</tbody></table> <br>"
        table_html += help_text_html
        return format_html(table_html)

    def create_table_for_order_items(self, order_items, oldest_order, latest_order):
        # Format dates to include time (hours and minutes)
        oldest_order_str = oldest_order.strftime('%d %B %Y, %H:%M')
        latest_order_str = latest_order.strftime('%d %B %Y, %H:%M')

        # Styled help text
        help_text_html = f"""
        <small style="display: block; font-size: 0.9rem; color: #666; margin-bottom: 10px;">
            <span> Sifarişlər <span style="font-weight: bold;">{oldest_order_str}</span> tarixdən <span style="font-weight: bold;">{latest_order_str}</span> tarixədək satılıb.</span>
        </small>
        """

        # Start building the table
        table_html = """
        <hr>
        <table class='table table-striped' style="border-collapse: collapse; width: 100%; margin-top: 20px; box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);">
            <caption style="caption-side: top; text-align: center; font-weight: bold; font-size: 1.5rem; padding-bottom: 8px; color: #444;">
                Satılmış Məhsullar
            </caption>
            <thead style="background-color: #f2f2f2;">
                <tr>
                    <th style="padding: 10px; border-bottom: 1px solid #ddd;">#</th>
                    <th style="padding: 10px; border-bottom: 1px solid #ddd;">Məhsul</th>
                    <th style="padding: 10px; border-bottom: 1px solid #ddd;">Miqdar</th>
                    <th style="padding: 10px; border-bottom: 1px solid #ddd;">Qiymət</th>
                </tr>
            </thead>
            <tbody>
        """

        total_price, total_quantity = 0, 0
        for index, item in enumerate(order_items, start=1):
            # Summing total price and quantity
            total_price += float(item["total_price"])
            total_quantity += int(item["total_quantity"])

            # Adding numbered rows
            table_html += f"""
                <tr style="background-color: {'#ffffff' if index % 2 == 0 else '#f9f9f9'};">
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{index}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item["meal__name"]}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item["total_quantity"]}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item["total_price"]} (AZN)</td>
                </tr>
            """

        # Adding total row at the end
        table_html += f"""
            <tr style="font-weight: bold; background-color: #e6e6e6;">
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">Cəmi</td>
                <td></td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{total_quantity}</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{total_price} (AZN)</td>
            </tr>
        """

        table_html += "</tbody></table> <br>"
        table_html += help_text_html
        return format_html(table_html)
