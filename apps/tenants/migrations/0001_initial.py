# Generated manually for multi-tenancy

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Restaurant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Restoran adı')),
                ('slug', models.SlugField(help_text='URL üçün unikal identifikator (məs: kazza-baku)', max_length=100, unique=True, verbose_name='Slug')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktiv')),
                ('address', models.TextField(blank=True, verbose_name='Ünvan')),
                ('phone', models.CharField(blank=True, max_length=30, verbose_name='Telefon')),
                ('owner_phone', models.CharField(blank=True, help_text='WhatsApp bildirişləri üçün (994XXXXXXXXX)', max_length=30, verbose_name='Sahib telefonu')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yaradılma tarixi')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Yenilənmə tarixi')),
            ],
            options={
                'verbose_name': 'Restoran',
                'verbose_name_plural': 'Restoranlar',
                'ordering': ['name'],
            },
        ),
    ]
