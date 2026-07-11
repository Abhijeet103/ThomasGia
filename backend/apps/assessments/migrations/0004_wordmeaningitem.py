from django.db import migrations, models


WORD_MEANING_SEED = [
    ("dawn", "dusk", "times_of_day", "hammer", "easy", ["time", "nature"]),
    ("cat", "dog", "animals", "ladder", "easy", ["animal"]),
    ("violin", "piano", "instruments", "carrot", "easy", ["music"]),
    ("orbit", "rotate", "space_motion", "blanket", "medium", ["space", "motion"]),
    ("opaque", "transparent", "material_property", "jungle", "medium", ["science"]),
    ("triangle", "square", "shapes", "justice", "easy", ["geometry"]),
    ("mercury", "venus", "planets", "teapot", "easy", ["space"]),
    ("frugal", "thrifty", "synonyms", "volcano", "hard", ["vocabulary"]),
    ("elated", "joyful", "synonyms", "compass", "medium", ["emotion"]),
    ("autumn", "spring", "seasons", "pillow", "easy", ["nature"]),
]


def seed_word_meaning_items(apps, schema_editor):
    WordMeaningItem = apps.get_model("assessments", "WordMeaningItem")
    if WordMeaningItem.objects.exists():
        return

    WordMeaningItem.objects.bulk_create(
        [
            WordMeaningItem(
                pair_word_1=pair_word_1,
                pair_word_2=pair_word_2,
                relationship_type=relationship_type,
                odd_word=odd_word,
                difficulty=difficulty,
                tags=tags,
                is_active=True,
            )
            for pair_word_1, pair_word_2, relationship_type, odd_word, difficulty, tags in WORD_MEANING_SEED
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0003_sectionprogress"),
    ]

    operations = [
        migrations.CreateModel(
            name="WordMeaningItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pair_word_1", models.CharField(max_length=128)),
                ("pair_word_2", models.CharField(max_length=128)),
                ("relationship_type", models.CharField(max_length=64)),
                ("odd_word", models.CharField(max_length=128)),
                ("difficulty", models.CharField(default="easy", max_length=16)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["difficulty", "id"],
            },
        ),
        migrations.RunPython(seed_word_meaning_items, migrations.RunPython.noop),
    ]
