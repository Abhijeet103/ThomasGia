from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0006_tenantuser_tenantmembership_tenant_user_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenantenrollmentcode",
            name="code",
            field=models.CharField(
                blank=True,
                default="",
                editable=False,
                help_text=(
                    "Full enrollment code retained for display to platform "
                    "administrators."
                ),
                max_length=32,
            ),
        ),
    ]
