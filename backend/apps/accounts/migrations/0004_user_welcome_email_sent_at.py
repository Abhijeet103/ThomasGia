from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_user_is_tenant_admin_user_tenant"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="welcome_email_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
