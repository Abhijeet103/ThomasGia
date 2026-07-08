from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    FREE = "free", "Free"
    PAID = "paid", "Paid"


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=UserRole.choices, default=UserRole.FREE)
    google_sub = models.CharField(max_length=255, blank=True, null=True, unique=True)
    subscription_expires_at = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    @property
    def is_paid_user(self) -> bool:
        return self.role == UserRole.PAID

    @property
    def has_active_subscription(self) -> bool:
        return bool(self.subscription_expires_at and self.subscription_expires_at > timezone.now())
