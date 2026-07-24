from __future__ import annotations

from django.conf import settings
from django.db import migrations


def seed_default_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.update_or_create(
        id=settings.SITE_ID,
        defaults={
            "domain": "mindmetric.store",
            "name": "MindMetric",
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_user_welcome_email_sent_at"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(seed_default_site, migrations.RunPython.noop),
    ]
