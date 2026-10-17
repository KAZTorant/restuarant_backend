from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tables', '0013_dedupe_and_unique_names'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0052_historicalstatistics_restaurant'),
        ('payments', '0007_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartialPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Məbləğ')),
                ('payment_type', models.CharField(choices=[('cash', 'Nağd'), ('card', 'Kart'), ('other', 'Digər')], max_length=20, verbose_name='Ödəniş növü')),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Endirim')),
                ('discount_comment', models.CharField(blank=True, max_length=255, verbose_name='Endirim səbəbi')),
                ('paid_at', models.DateTimeField(auto_now_add=True, verbose_name='Ödəmə tarixi')),
                ('orders', models.ManyToManyField(related_name='partial_payments', to='orders.order', verbose_name='Sifarişlər')),
                ('paid_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Operator')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='partial_payments', to='payments.payment', verbose_name='Ödəniş')),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='partial_payments', to='tables.table', verbose_name='Masa')),
            ],
            options={
                'verbose_name': 'Qismən ödəniş',
                'verbose_name_plural': 'Qismən ödənişlər',
                'ordering': ['paid_at', 'id'],
            },
        ),
    ]
