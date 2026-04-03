import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_token():
    return secrets.token_hex(32)


def default_expiry():
    return timezone.now() + timedelta(days=30)


class AdminAuthToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_tokens',
        verbose_name="İstifadəçi"
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_token,
        verbose_name="Token"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaradılma tarixi")
    expires_at = models.DateTimeField(default=default_expiry, verbose_name="Bitmə tarixi")
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name="Son istifadə tarixi")

    class Meta:
        verbose_name = "Admin Auth Token"
        verbose_name_plural = "Admin Auth Tokens"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.token[:12]}..."

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def refresh(self):
        """Token-in bitmə müddətini uzat"""
        self.expires_at = timezone.now() + timedelta(days=30)
        self.last_used_at = timezone.now()
        self.save(update_fields=["expires_at", "last_used_at"])
        self.save(update_fields=["expires_at", "last_used_at"])
