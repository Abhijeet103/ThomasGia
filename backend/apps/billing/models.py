from __future__ import annotations

from django.conf import settings
from django.db import models


class SubscriptionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    CANCELED = "canceled", "Canceled"
    EXPIRED = "expired", "Expired"


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="subscriptions", blank=True, null=True)
    provider = models.CharField(max_length=32, default="stripe")
    plan_code = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=SubscriptionStatus.choices, default=SubscriptionStatus.PENDING)
    provider_customer_id = models.CharField(max_length=255, blank=True)
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.email} - {self.plan_code} - {self.status}"
