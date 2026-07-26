from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0003_sync_tenant_assessment_visibility"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tenant",
            name="default_plan_code",
            field=models.CharField(
                "default plan",
                blank=True,
                choices=[
                    ("weekly", "Weekly"),
                    ("monthly", "Monthly"),
                    ("yearly", "Yearly"),
                ],
                default=None,
                help_text=(
                    "Optional plan automatically granted when a member joins. "
                    "Leave blank to require a manual membership grant."
                ),
                max_length=16,
                null=True,
            ),
        ),
    ]
