from django.db import models
from django.utils.text import slugify


class Restaurant(models.Model):
    name = models.CharField(max_length=200, verbose_name='Restoran adı')
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='Slug',
        help_text='URL üçün unikal identifikator (məs: kazza-baku)',
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktiv')
    address = models.TextField(blank=True, verbose_name='Ünvan')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Telefon')
    owner_phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Sahib telefonu',
        help_text='WhatsApp bildirişləri üçün (994XXXXXXXXX)',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaradılma tarixi')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Yenilənmə tarixi')

    class Meta:
        verbose_name = 'Restoran'
        verbose_name_plural = 'Restoranlar'
        ordering = ['name']

    def __str__(self):
        status = '' if self.is_active else ' (deaktiv)'
        return f'{self.name}{status}'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'restoran'
            slug = base_slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
