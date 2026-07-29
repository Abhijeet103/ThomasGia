from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class BillingPlanCode(models.TextChoices):
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"


class BillingPlan(models.Model):
    code = models.CharField(max_length=16, choices=BillingPlanCode.choices, unique=True)
    title = models.CharField(max_length=80)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        blank=True,
        null=True,
        help_text="Optional amount charged at checkout. Leave blank to charge the regular price.",
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="Three-letter ISO currency code, for example USD.",
    )
    duration_label = models.CharField(max_length=120)
    summary = models.TextField()
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("display_order", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(sale_price__isnull=True) | Q(sale_price__lte=F("price")),
                name="billing_plan_sale_lte_price",
            ),
        ]

    def clean(self):
        super().clean()
        if self.sale_price is not None and self.sale_price > self.price:
            raise ValidationError(
                {"sale_price": "Sale price cannot be greater than the regular price."}
            )

    def save(self, *args, **kwargs):
        self.currency = self.currency.strip().upper()
        super().save(*args, **kwargs)

    @property
    def price_display(self) -> str:
        if self.currency == "USD":
            return f"${self.price:.2f}"
        return f"{self.currency} {self.price:.2f}"

    @property
    def effective_price(self) -> Decimal:
        return self.sale_price if self.sale_price is not None else self.price

    @property
    def effective_price_display(self) -> str:
        if self.currency == "USD":
            return f"${self.effective_price:.2f}"
        return f"{self.currency} {self.effective_price:.2f}"

    @property
    def has_discount(self) -> bool:
        return self.sale_price is not None and self.sale_price < self.price

    @property
    def discount_percent(self) -> int:
        if not self.has_discount:
            return 0
        discount = ((self.price - self.sale_price) / self.price) * Decimal("100")
        return int(discount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def __str__(self) -> str:
        return f"{self.title} ({self.effective_price_display})"


class SubscriptionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    CANCELED = "canceled", "Canceled"
    EXPIRED = "expired", "Expired"


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="subscriptions", blank=True, null=True)
    tenant_user = models.ForeignKey(
        "tenants.TenantUser",
        on_delete=models.PROTECT,
        related_name="subscriptions",
        blank=True,
        null=True,
    )
    provider = models.CharField(max_length=32, default="stripe")
    plan_code = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=SubscriptionStatus.choices, default=SubscriptionStatus.PENDING)
    provider_customer_id = models.CharField(max_length=255, blank=True)
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status", "updated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.plan_code} - {self.status}"
