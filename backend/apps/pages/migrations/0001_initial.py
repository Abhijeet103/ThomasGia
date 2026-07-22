from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SaleInquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(blank=True, max_length=255)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(blank=True, max_length=64)),
                ("organization", models.CharField(blank=True, max_length=255)),
                ("team_size", models.CharField(blank=True, max_length=64)),
                ("message", models.TextField()),
                ("source_page", models.CharField(blank=True, max_length=64)),
                ("status", models.CharField(choices=[("new", "New"), ("contacted", "Contacted"), ("closed", "Closed")], default="new", max_length=24)),
                ("notes", models.TextField(blank=True)),
                ("contacted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
