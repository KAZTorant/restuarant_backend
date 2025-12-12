from datetime import date, datetime, time

from django import forms
from django.contrib import admin, messages
from django.db.models import Q, Sum
from django.forms import DateField, ModelForm, TimeField
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.payments.models import Payment, PaymentCalculation


class PaymentCalculationForm(forms.Form):
    start_date = forms.DateField(
        label=_("Başlanğıc tarixi"),
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=date.today()
    )
    end_date = forms.DateField(
        label=_("Son tarixi"),
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=date.today()
    )
    start_time = forms.CharField(
        label=_("Başlanğıc saatı (SS:DD)"),
        max_length=5,
        widget=forms.TextInput(attrs={
            'placeholder': '12:00',
            'pattern': '[0-2][0-9]:[0-5][0-9]',
            'title': '24 saat formatı (SS:DD)',
            'class': 'time-input-24h',
            'value': '12:00'
        }),
        initial='12:00'
    )
    end_time = forms.CharField(
        label=_("Son saatı (SS:DD)"),
        max_length=5,
        widget=forms.TextInput(attrs={
            'placeholder': '23:59',
            'pattern': '[0-2][0-9]:[0-5][0-9]',
            'title': '24 saat formatı (SS:DD)',
            'class': 'time-input-24h',
            'value': '23:59'
        }),
        initial='23:59'
    )

    def clean_start_time(self):
        time_str = self.cleaned_data.get('start_time')
        if not time_str:
            return time(12, 0)
        
        try:
            hours, minutes = map(int, time_str.split(':'))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return time(hours, minutes)
            raise forms.ValidationError(_('Yanlış saat formatı. 00:00-23:59 arasında olmalıdır'))
        except (ValueError, AttributeError):
            raise forms.ValidationError(_('Yanlış saat formatı. SS:DD formatında daxil edin (məsələn: 14:30)'))

    def clean_end_time(self):
        time_str = self.cleaned_data.get('end_time')
        if not time_str:
            return time(23, 59)
        
        try:
            hours, minutes = map(int, time_str.split(':'))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return time(hours, minutes)
            raise forms.ValidationError(_('Yanlış saat formatı. 00:00-23:59 arasında olmalıdır'))
        except (ValueError, AttributeError):
            raise forms.ValidationError(_('Yanlış saat formatı. SS:DD formatında daxil edin (məsələn: 14:30)'))


@admin.register(PaymentCalculation)
class PaymentCalculationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'date_range_display',
        'time_range_display',
        'total_amount',
        'payment_count',
        'cash_amount',
        'card_amount',
        'other_amount',
        'created_by',
        'created_at',
    )
    list_filter = (
        'start_date',
        'end_date',
        'created_by',
        'created_at',
    )
    search_fields = (
        'created_by__username',
    )
    readonly_fields = (
        'total_amount',
        'payment_count',
        'cash_amount',
        'card_amount',
        'other_amount',
        'created_by',
        'created_at',
        'date_range_display',
        'time_range_display',
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'calculate/',
                self.admin_site.admin_view(self.calculate_payments_view),
                name='payments_paymentcalculation_calculate'
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['calculate_url'] = reverse('admin:payments_paymentcalculation_calculate')
        return super().changelist_view(request, extra_context)

    def calculate_payments_view(self, request):
        if request.method == 'POST':
            form = PaymentCalculationForm(request.POST)
            if form.is_valid():
                start_date = form.cleaned_data['start_date']
                end_date = form.cleaned_data['end_date']
                start_time = form.cleaned_data['start_time']
                end_time = form.cleaned_data['end_time']

                # Combine date and time for filtering
                start_datetime = datetime.combine(start_date, start_time)
                end_datetime = datetime.combine(end_date, end_time)

                # Make timezone aware
                if timezone.is_naive(start_datetime):
                    start_datetime = timezone.make_aware(start_datetime)
                if timezone.is_naive(end_datetime):
                    end_datetime = timezone.make_aware(end_datetime)

                # Filter payments by datetime range
                payments = Payment.objects.filter(
                    paid_at__gte=start_datetime,
                    paid_at__lte=end_datetime
                )

                # Calculate totals
                total_amount = payments.aggregate(
                    total=Sum('final_price')
                )['total'] or 0

                payment_count = payments.count()

                # Calculate amounts by payment type
                cash_amount = 0
                card_amount = 0
                other_amount = 0

                for payment in payments:
                    if payment.payment_methods.exists():
                        # If payment has multiple payment methods
                        for method in payment.payment_methods.all():
                            if method.payment_type == 'cash':
                                cash_amount += method.amount
                            elif method.payment_type == 'card':
                                card_amount += method.amount
                            else:
                                other_amount += method.amount
                    else:
                        # If payment has only one payment type
                        if payment.payment_type == 'cash':
                            cash_amount += payment.paid_amount
                        elif payment.payment_type == 'card':
                            card_amount += payment.paid_amount
                        else:
                            other_amount += payment.paid_amount

                # Create calculation record
                calculation = PaymentCalculation.objects.create(
                    start_date=start_date,
                    end_date=end_date,
                    start_time=start_time,
                    end_time=end_time,
                    total_amount=total_amount,
                    payment_count=payment_count,
                    cash_amount=cash_amount,
                    card_amount=card_amount,
                    other_amount=other_amount,
                    created_by=request.user
                )

                messages.success(
                    request,
                    _(f'Hesablama uğurla yaradıldı. Ümumi: {total_amount}₼, Sayı: {payment_count}')
                )

                return HttpResponseRedirect(
                    reverse('admin:payments_paymentcalculation_changelist')
                )
        else:
            form = PaymentCalculationForm()

        context = {
            'title': _('Ödəniş hesablaması'),
            'form': form,
            'opts': self.model._meta,
        }

        return render(request, 'admin/payments/payment_calculation_form.html', context)

    def has_add_permission(self, request):
        return False  # Don't allow manual addition, only through calculation

    def has_change_permission(self, request, obj=None):
        return False  # Read-only calculations

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superuser can delete calculations