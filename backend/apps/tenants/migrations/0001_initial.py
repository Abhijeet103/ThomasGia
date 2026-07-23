from __future__ import annotations

import os
from urllib.parse import urlparse

from django.db import migrations, models


def create_default_tenant(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    site_url = os.getenv("SITE_URL", "https://mindmetric.store")
    host = (urlparse(site_url).hostname or "mindmetric.store").lower()
    Tenant.objects.get_or_create(
        slug=os.getenv("DEFAULT_TENANT_SLUG", "mindmetric"),
        defaults={
            "name": "MindMetric",
            "primary_domain": host,
            "is_active": True,
        },
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(unique=True)),
                ("primary_domain", models.CharField(max_length=255, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.RunPython(create_default_tenant, migrations.RunPython.noop),
    ]
