from django.db import migrations


ADDITIONAL_WORD_MEANING_SEED = [
    ("oak", "pine", "trees", "teacup", "easy", ["nature", "plants"]),
    ("sparrow", "eagle", "birds", "helmet", "easy", ["animals", "nature"]),
    ("bus", "train", "transport", "candle", "easy", ["travel"]),
    ("spoon", "fork", "cutlery", "blanket", "easy", ["home"]),
    ("doctor", "nurse", "healthcare_roles", "volcano", "easy", ["jobs"]),
    ("red", "blue", "colors", "pencil", "easy", ["basics"]),
    ("soccer", "tennis", "sports", "ladder", "easy", ["activities"]),
    ("apple", "banana", "fruits", "hammer", "easy", ["food"]),
    ("winter", "summer", "seasons", "wallet", "easy", ["time", "nature"]),
    ("circle", "triangle", "shapes", "blanket", "easy", ["geometry"]),
    ("teacher", "student", "school_people", "jungle", "easy", ["education"]),
    ("bread", "rice", "staple_foods", "compass", "easy", ["food"]),
    ("lion", "tiger", "wild_cats", "microwave", "medium", ["animals"]),
    ("violin", "cello", "string_instruments", "helmet", "medium", ["music"]),
    ("mercury", "mars", "planets", "blanket", "medium", ["space"]),
    ("granite", "marble", "rocks", "umbrella", "medium", ["earth_science"]),
    ("river", "stream", "water_bodies", "lantern", "medium", ["geography"]),
    ("honest", "truthful", "synonyms", "suitcase", "medium", ["vocabulary"]),
    ("rapid", "swift", "synonyms", "teapot", "medium", ["vocabulary"]),
    ("ancient", "historic", "related_terms", "carrot", "medium", ["history"]),
    ("frigid", "icy", "temperature_terms", "guitar", "medium", ["weather"]),
    ("orbit", "revolve", "space_motion", "kettle", "medium", ["space", "motion"]),
    ("scarlet", "crimson", "color_family", "ladder", "medium", ["colors"]),
    ("island", "peninsula", "landforms", "toaster", "medium", ["geography"]),
    ("justice", "fairness", "abstract_values", "mushroom", "medium", ["abstract"]),
    ("glacier", "iceberg", "ice_formations", "wallet", "medium", ["nature"]),
    ("baker", "carpenter", "trades", "saturn", "medium", ["jobs"]),
    ("tablet", "capsule", "medicine_forms", "lantern", "medium", ["health"]),
    ("budget", "saving", "money_management", "volcano", "medium", ["finance"]),
    ("nectar", "pollen", "flower_terms", "helmet", "medium", ["plants"]),
    ("meticulous", "careful", "related_traits", "asteroid", "hard", ["vocabulary"]),
    ("eloquent", "articulate", "synonyms", "wheelbarrow", "hard", ["vocabulary"]),
    ("resilient", "durable", "related_traits", "sapphire", "hard", ["vocabulary"]),
    ("obscure", "vague", "related_traits", "cactus", "hard", ["vocabulary"]),
    ("candid", "frank", "synonyms", "tractor", "hard", ["vocabulary"]),
    ("lucid", "clear", "related_traits", "penguin", "hard", ["vocabulary"]),
    ("frugal", "economical", "synonyms", "meteor", "hard", ["vocabulary"]),
    ("ardent", "passionate", "synonyms", "helmet", "hard", ["vocabulary"]),
    ("placid", "calm", "synonyms", "submarine", "hard", ["vocabulary"]),
    ("tenacious", "persistent", "synonyms", "orchid", "hard", ["vocabulary"]),
    ("nebula", "galaxy", "space_objects", "ladder", "hard", ["space"]),
    ("alloy", "ore", "metal_terms", "parachute", "hard", ["science"]),
    ("enzyme", "protein", "biology_terms", "teacup", "hard", ["science"]),
    ("quartz", "basalt", "geology_terms", "wallet", "hard", ["earth_science"]),
    ("sonnet", "haiku", "poetry_forms", "microscope", "hard", ["literature"]),
    ("harbor", "port", "maritime_places", "candle", "hard", ["geography"]),
    ("equity", "assets", "finance_terms", "giraffe", "hard", ["finance"]),
    ("drought", "monsoon", "climate_terms", "screwdriver", "hard", ["weather"]),
]


def seed_more_word_meaning_items(apps, schema_editor):
    WordMeaningItem = apps.get_model("assessments", "WordMeaningItem")
    existing_keys = {
        (item.pair_word_1, item.pair_word_2, item.odd_word, item.difficulty)
        for item in WordMeaningItem.objects.all().only("pair_word_1", "pair_word_2", "odd_word", "difficulty")
    }

    rows_to_create = []
    for pair_word_1, pair_word_2, relationship_type, odd_word, difficulty, tags in ADDITIONAL_WORD_MEANING_SEED:
        key = (pair_word_1, pair_word_2, odd_word, difficulty)
        if key in existing_keys:
            continue
        rows_to_create.append(
            WordMeaningItem(
                pair_word_1=pair_word_1,
                pair_word_2=pair_word_2,
                relationship_type=relationship_type,
                odd_word=odd_word,
                difficulty=difficulty,
                tags=tags,
                is_active=True,
            )
        )

    if rows_to_create:
        WordMeaningItem.objects.bulk_create(rows_to_create)


class Migration(migrations.Migration):

    dependencies = [
        ("assessments", "0004_wordmeaningitem"),
    ]

    operations = [
        migrations.RunPython(seed_more_word_meaning_items, migrations.RunPython.noop),
    ]
