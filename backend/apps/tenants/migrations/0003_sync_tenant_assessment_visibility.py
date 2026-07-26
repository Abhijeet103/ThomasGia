from django.db import migrations


TRACK_DEFAULTS = {
    "prepgia": {
        "title": "Thomas GIA",
        "description": "Thomas GIA-style speed practice with full tests and section-wise drills.",
        "module_count": 5,
        "trust_line": "Used by 30,000+ employers across the UK and Europe",
        "available_languages": ["English"],
        "default_visibility": "accessible",
    },
    "ccat": {
        "title": "CCAT",
        "description": "Numerical, verbal, and abstract aptitude practice with module drills and full tests.",
        "module_count": 3,
        "trust_line": "Taken 10M+ times at 4,500+ US employers",
        "available_languages": ["English"],
        "default_visibility": "accessible",
    },
    "watson_glaser": {
        "title": "Watson-Glaser",
        "description": "Critical reasoning practice covering inference, assumptions, and argument evaluation.",
        "module_count": 4,
        "trust_line": "In testing with a small group right now",
        "available_languages": ["English"],
        "default_visibility": "upcoming",
    },
    "shl_verify": {
        "title": "SHL Verify",
        "description": "Numerical, verbal, and inductive reasoning practice in the SHL question style.",
        "module_count": 4,
        "trust_line": "In testing with a small group right now",
        "available_languages": ["English"],
        "default_visibility": "upcoming",
    },
}


def sync_existing_tenant_tracks(apps, schema_editor):
    Tenant = apps.get_model("tenants", "Tenant")
    AssessmentTrack = apps.get_model("assessments", "AssessmentTrack")

    for tenant in Tenant.objects.all():
        allowed_assessments = set(tenant.allowed_assessments or [])
        for assessment_type, defaults in TRACK_DEFAULTS.items():
            is_allocated = assessment_type in allowed_assessments
            track, created = AssessmentTrack.objects.get_or_create(
                tenant=tenant,
                assessment_type=assessment_type,
                defaults={
                    "title": defaults["title"],
                    "description": defaults["description"],
                    "module_count": defaults["module_count"],
                    "trust_line": defaults["trust_line"],
                    "available_languages": defaults["available_languages"],
                    "visibility_state": (
                        defaults["default_visibility"]
                        if is_allocated
                        else "hidden"
                    ),
                    "is_active": is_allocated,
                },
            )
            if created:
                continue

            update_fields = []
            if not is_allocated and track.visibility_state != "hidden":
                track.visibility_state = "hidden"
                update_fields.append("visibility_state")
            if track.is_active != is_allocated:
                track.is_active = is_allocated
                update_fields.append("is_active")
            if update_fields:
                track.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0012_assessmenttrack_assessmenttrackwaitlistentry"),
        ("tenants", "0002_tenant_allowed_assessments_tenant_default_plan_code_and_more"),
    ]

    operations = [
        migrations.RunPython(sync_existing_tenant_tracks, migrations.RunPython.noop),
    ]
