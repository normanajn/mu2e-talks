import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class ApiToken(models.Model):
    name = models.CharField(max_length=120)
    prefix = models.CharField(max_length=16, db_index=True)
    key_hash = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='api_tokens',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def hash_key(key):
        return hashlib.sha256(key.encode('utf-8')).hexdigest()

    @classmethod
    def create_token(cls, user, name):
        key = f'mu2e_{secrets.token_urlsafe(32)}'
        token = cls.objects.create(
            user=user,
            name=name,
            prefix=key[:16],
            key_hash=cls.hash_key(key),
        )
        return token, key

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at', 'updated_at'])

    def __str__(self):
        return f'{self.name} ({self.prefix}...)'
