from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0008_attemptsection_summary_counts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attemptsection",
            name="section_type",
            field=models.CharField(
                choices=[
                    ("reasoning", "Reasoning"),
                    ("perceptual_speed", "Perceptual Speed"),
                    ("number_speed_accuracy", "Number Speed & Accuracy"),
                    ("word_meaning", "Word Meaning"),
                    ("spatial_visualization", "Spatial Visualization"),
                    ("ccat_numerical", "CCAT Math & Numerical Reasoning"),
                    ("ccat_verbal", "CCAT Verbal Reasoning"),
                    ("ccat_spatial", "CCAT Spatial & Abstract Reasoning"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="sectionprogress",
            name="section_type",
            field=models.CharField(
                choices=[
                    ("reasoning", "Reasoning"),
                    ("perceptual_speed", "Perceptual Speed"),
                    ("number_speed_accuracy", "Number Speed & Accuracy"),
                    ("word_meaning", "Word Meaning"),
                    ("spatial_visualization", "Spatial Visualization"),
                    ("ccat_numerical", "CCAT Math & Numerical Reasoning"),
                    ("ccat_verbal", "CCAT Verbal Reasoning"),
                    ("ccat_spatial", "CCAT Spatial & Abstract Reasoning"),
                ],
                max_length=32,
            ),
        ),
    ]
