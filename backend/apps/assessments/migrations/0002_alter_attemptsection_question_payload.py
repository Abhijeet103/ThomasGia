from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attemptsection",
            name="question_payload",
            field=models.JSONField(default=dict),
        ),
    ]
