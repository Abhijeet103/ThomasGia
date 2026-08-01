from django.db import migrations, models
from django.db.models import Q


def convert_india_prices_to_usd(apps, schema_editor):
    BillingPlan = apps.get_model("billing", "BillingPlan")
    BillingPlanCountryPrice = apps.get_model("billing", "BillingPlanCountryPrice")

    for plan in BillingPlan.objects.all():
        BillingPlanCountryPrice.objects.update_or_create(
            plan=plan,
            country_code="IN",
            defaults={
                "currency": "USD",
                "price": plan.price,
                "sale_price": plan.sale_price,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0007_billingplancountryprice"),
    ]

    operations = [
        migrations.RunPython(convert_india_prices_to_usd, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="billingplancountryprice",
            constraint=models.CheckConstraint(
                condition=~Q(country_code="IN") | Q(currency="USD"),
                name="billing_india_price_uses_usd",
            ),
        ),
    ]
