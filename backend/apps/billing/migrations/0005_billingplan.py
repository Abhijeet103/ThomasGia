from decimal import Decimal

from django.db import migrations, models
import django.core.validators


def seed_billing_plans(apps, schema_editor):
    BillingPlan = apps.get_model("billing", "BillingPlan")
    plans = (
        {
            "code": "weekly",
            "title": "Weekly",
            "price": Decimal("9.99"),
            "currency": "USD",
            "duration_label": "7 days access",
            "summary": "Unlimited full tests and section-wise tests for one week.",
            "display_order": 10,
        },
        {
            "code": "monthly",
            "title": "Monthly",
            "price": Decimal("19.99"),
            "currency": "USD",
            "duration_label": "1 month access",
            "summary": "Unlimited full tests and section-wise tests for one month.",
            "display_order": 20,
        },
        {
            "code": "yearly",
            "title": "Yearly",
            "price": Decimal("12.99"),
            "currency": "USD",
            "duration_label": "1 year access",
            "summary": "Unlimited full tests and section-wise tests for one year.",
            "display_order": 30,
        },
    )
    for plan in plans:
        BillingPlan.objects.update_or_create(code=plan["code"], defaults=plan)


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0004_subscription_tenant_user"),
    ]

    operations = [
        migrations.CreateModel(
            name="BillingPlan",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        choices=[
                            ("weekly", "Weekly"),
                            ("monthly", "Monthly"),
                            ("yearly", "Yearly"),
                        ],
                        max_length=16,
                        unique=True,
                    ),
                ),
                ("title", models.CharField(max_length=80)),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        default="USD",
                        help_text="Three-letter ISO currency code, for example USD.",
                        max_length=3,
                    ),
                ),
                ("duration_label", models.CharField(max_length=120)),
                ("summary", models.TextField()),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("display_order", "id")},
        ),
        migrations.RunPython(seed_billing_plans, migrations.RunPython.noop),
    ]
