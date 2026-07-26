from django.db import migrations


TRACKS = {
    "prepgia": {
        "title": "Thomas GIA",
        "description": "Thomas GIA-style speed practice with full tests and section-wise drills.",
        "module_count": 5,
        "trust_line": "Used by 30,000+ employers across the UK and Europe",
        "available_languages": ["English"],
        "visibility_state": "accessible",
        "is_active": True,
    },
    "ccat": {
        "title": "CCAT",
        "description": "Numerical, verbal, and abstract aptitude practice with module drills and full tests.",
        "module_count": 3,
        "trust_line": "Taken 10M+ times at 4,500+ US employers",
        "available_languages": ["English"],
        "visibility_state": "accessible",
        "is_active": True,
    },
    "watson_glaser": {
        "title": "Watson-Glaser",
        "description": "Critical reasoning practice covering inference, assumptions, and argument evaluation.",
        "module_count": 4,
        "trust_line": "In testing with a small group right now",
        "available_languages": ["English"],
        "visibility_state": "hidden",
        "is_active": False,
    },
    "shl_verify": {
        "title": "SHL Verify",
        "description": "Numerical, verbal, and inductive reasoning practice in the SHL question style.",
        "module_count": 4,
        "trust_line": "In testing with a small group right now",
        "available_languages": ["English"],
        "visibility_state": "hidden",
        "is_active": False,
    },
}


def seed_demo_tenant(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    AssessmentTrack = apps.get_model("assessments", "AssessmentTrack")

    tenant, _ = Tenant.objects.update_or_create(
        slug="demo",
        defaults={
            "name": "Demo",
            "primary_domain": "demo.mindmetric.store",
            "tenant_type": "institution",
            "subdomain_prefix": "demo",
            "enrollment_mode": "open",
            "default_plan_code": "weekly",
            "allowed_assessments": ["prepgia", "ccat"],
            "is_active": True,
        },
    )

    for assessment_type, defaults in TRACKS.items():
        AssessmentTrack.objects.update_or_create(
            tenant=tenant,
            assessment_type=assessment_type,
            defaults=defaults,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("assessments", "0012_assessmenttrack_assessmenttrackwaitlistentry"),
        ("tenants", "0004_tenant_default_plan_optional"),
    ]

    operations = [
        migrations.RunPython(seed_demo_tenant, migrations.RunPython.noop),
    ]
