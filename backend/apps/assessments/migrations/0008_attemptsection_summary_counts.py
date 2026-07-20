from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0007_multi_assessment_support"),
    ]

    operations = [
        migrations.AddField(
            model_name="attemptsection",
            name="correct_answers_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="attemptsection",
            name="incorrect_answers_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
