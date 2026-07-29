from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0005_billingplan"),
    ]

    operations = [
        migrations.AddField(
            model_name="billingplan",
            name="sale_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    "Optional amount charged at checkout. "
                    "Leave blank to charge the regular price."
                ),
                max_digits=10,
                null=True,
                validators=[MinValueValidator(Decimal("0.01"))],
            ),
        ),
        migrations.AddConstraint(
            model_name="billingplan",
            constraint=models.CheckConstraint(
                condition=Q(sale_price__isnull=True)
                | Q(sale_price__lte=F("price")),
                name="billing_plan_sale_lte_price",
            ),
        ),
    ]
