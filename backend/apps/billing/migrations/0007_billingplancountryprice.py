from decimal import Decimal, ROUND_HALF_UP

from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import F, Q


def seed_regional_prices(apps, schema_editor):
    BillingPlan = apps.get_model("billing", "BillingPlan")
    BillingPlanCountryPrice = apps.get_model("billing", "BillingPlanCountryPrice")
    regions = (
        ("GB", "GBP", Decimal("0.80")),
        ("EU", "EUR", Decimal("0.92")),
        ("IN", "INR", Decimal("83.00")),
    )
    for plan in BillingPlan.objects.all():
        for country_code, currency, multiplier in regions:
            price = (plan.price * multiplier).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            sale_price = None
            if plan.sale_price is not None:
                sale_price = (plan.sale_price * multiplier).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
            BillingPlanCountryPrice.objects.get_or_create(
                plan=plan,
                country_code=country_code,
                defaults={
                    "currency": currency,
                    "price": price,
                    "sale_price": sale_price,
                    "is_active": True,
                },
            )


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0006_billingplan_sale_price"),
    ]

    operations = [
        migrations.CreateModel(
            name="BillingPlanCountryPrice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("country_code", models.CharField(help_text="Two-letter ISO country code. Use EU for the shared European price. An exact country override takes precedence over EU.", max_length=2)),
                ("currency", models.CharField(choices=[("USD", "US dollar"), ("GBP", "British pound"), ("EUR", "Euro"), ("INR", "Indian rupee")], max_length=3)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal("0.01"))])),
                ("sale_price", models.DecimalField(blank=True, decimal_places=2, help_text="Optional regional sale price charged at checkout.", max_digits=10, null=True, validators=[MinValueValidator(Decimal("0.01"))])),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="country_prices", to="billing.billingplan")),
            ],
            options={"ordering": ("plan__display_order", "country_code")},
        ),
        migrations.AddConstraint(
            model_name="billingplancountryprice",
            constraint=models.UniqueConstraint(fields=("plan", "country_code"), name="billing_plan_country_price_unique"),
        ),
        migrations.AddConstraint(
            model_name="billingplancountryprice",
            constraint=models.CheckConstraint(condition=Q(sale_price__isnull=True) | Q(sale_price__lte=F("price")), name="billing_country_sale_lte_price"),
        ),
        migrations.RunPython(seed_regional_prices, migrations.RunPython.noop),
    ]
