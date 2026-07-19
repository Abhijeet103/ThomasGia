from django.db import migrations, models


def backfill_assessment_type(apps, schema_editor):
    Attempt = apps.get_model("assessments", "Attempt")
    SectionProgress = apps.get_model("assessments", "SectionProgress")
    Attempt.objects.filter(assessment_type="").update(assessment_type="prepgia")
    SectionProgress.objects.filter(assessment_type="").update(assessment_type="prepgia")


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0006_expand_wordmeaning_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="attempt",
            name="assessment_type",
            field=models.CharField(default="prepgia", max_length=24),
        ),
        migrations.AddField(
            model_name="sectionprogress",
            name="assessment_type",
            field=models.CharField(default="prepgia", max_length=24),
        ),
        migrations.RunPython(backfill_assessment_type, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="sectionprogress",
            unique_together={("user", "assessment_type", "section_type")},
        ),
    ]
