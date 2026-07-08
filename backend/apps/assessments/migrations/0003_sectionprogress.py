from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0002_alter_attemptsection_question_payload"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SectionProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section_type", models.CharField(choices=[("reasoning", "Reasoning"), ("perceptual_speed", "Perceptual Speed"), ("number_speed_accuracy", "Number Speed & Accuracy"), ("word_meaning", "Word Meaning"), ("spatial_visualization", "Spatial Visualization")], max_length=32)),
                ("practice_questions_solved", models.PositiveIntegerField(default=0)),
                ("tests_taken", models.PositiveIntegerField(default=0)),
                ("last_test_score", models.FloatField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="section_progress", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("user", "section_type")},
            },
        ),
    ]
