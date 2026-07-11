from django.db import migrations


WORD_MEANING_CATALOG = {
    "easy": {
        "fruits": {
            "pairs": [("apple", "mango"), ("banana", "orange"), ("grape", "pear"), ("guava", "papaya")],
            "odd_words": ["hammer", "lantern", "pillow"],
            "tags": ["food", "basics"],
        },
        "animals": {
            "pairs": [("tiger", "leopard"), ("rabbit", "hamster"), ("zebra", "giraffe"), ("goat", "sheep")],
            "odd_words": ["teapot", "ladder", "wallet"],
            "tags": ["animals", "basics"],
        },
        "birds": {
            "pairs": [("sparrow", "robin"), ("eagle", "falcon"), ("parrot", "macaw"), ("pigeon", "dove")],
            "odd_words": ["blanket", "helmet", "kettle"],
            "tags": ["animals", "nature"],
        },
        "vehicles": {
            "pairs": [("bus", "van"), ("train", "tram"), ("bicycle", "scooter"), ("truck", "lorry")],
            "odd_words": ["candle", "carpet", "pencil"],
            "tags": ["travel"],
        },
        "colors": {
            "pairs": [("red", "blue"), ("green", "yellow"), ("purple", "orange"), ("black", "white")],
            "odd_words": ["notebook", "hammer", "teacup"],
            "tags": ["basics"],
        },
        "shapes": {
            "pairs": [("circle", "square"), ("triangle", "rectangle"), ("oval", "diamond"), ("hexagon", "pentagon")],
            "odd_words": ["blanket", "toaster", "wallet"],
            "tags": ["geometry"],
        },
        "school_items": {
            "pairs": [("pencil", "eraser"), ("notebook", "ruler"), ("marker", "crayon"), ("backpack", "folder")],
            "odd_words": ["volcano", "jungle", "planet"],
            "tags": ["education"],
        },
        "body_parts": {
            "pairs": [("hand", "foot"), ("knee", "elbow"), ("eye", "ear"), ("finger", "toe")],
            "odd_words": ["suitcase", "helmet", "ladder"],
            "tags": ["human_body"],
        },
        "weather_terms": {
            "pairs": [("rain", "snow"), ("cloud", "wind"), ("storm", "fog"), ("thunder", "lightning")],
            "odd_words": ["pillow", "teapot", "wallet"],
            "tags": ["weather", "nature"],
        },
        "clothes": {
            "pairs": [("shirt", "jacket"), ("socks", "gloves"), ("scarf", "hat"), ("skirt", "trousers")],
            "odd_words": ["lantern", "microwave", "hammer"],
            "tags": ["daily_life"],
        },
        "furniture": {
            "pairs": [("chair", "table"), ("sofa", "stool"), ("desk", "shelf"), ("bench", "cabinet")],
            "odd_words": ["guitar", "pencil", "helmet"],
            "tags": ["home"],
        },
        "jobs": {
            "pairs": [("doctor", "nurse"), ("teacher", "coach"), ("pilot", "captain"), ("farmer", "gardener")],
            "odd_words": ["volcano", "toaster", "blanket"],
            "tags": ["jobs"],
        },
        "sports": {
            "pairs": [("tennis", "badminton"), ("soccer", "hockey"), ("cricket", "baseball"), ("boxing", "wrestling")],
            "odd_words": ["ladder", "teacup", "wallet"],
            "tags": ["activities"],
        },
        "vegetables": {
            "pairs": [("carrot", "radish"), ("potato", "onion"), ("spinach", "cabbage"), ("peas", "beans")],
            "odd_words": ["helmet", "notebook", "pillow"],
            "tags": ["food"],
        },
    },
    "medium": {
        "planets": {
            "pairs": [("mercury", "venus"), ("earth", "mars"), ("jupiter", "saturn"), ("uranus", "neptune")],
            "odd_words": ["blanket", "lantern", "carrot"],
            "tags": ["space"],
        },
        "landforms": {
            "pairs": [("island", "peninsula"), ("valley", "canyon"), ("plateau", "plain"), ("glacier", "fjord")],
            "odd_words": ["helmet", "wallet", "microwave"],
            "tags": ["geography"],
        },
        "rocks": {
            "pairs": [("granite", "marble"), ("basalt", "quartz"), ("slate", "shale"), ("limestone", "sandstone")],
            "odd_words": ["teapot", "umbrella", "pillow"],
            "tags": ["earth_science"],
        },
        "music_terms": {
            "pairs": [("violin", "cello"), ("trumpet", "trombone"), ("flute", "clarinet"), ("drum", "tambourine")],
            "odd_words": ["helmet", "wallet", "ladder"],
            "tags": ["music"],
        },
        "water_bodies": {
            "pairs": [("river", "stream"), ("ocean", "sea"), ("pond", "lake"), ("bay", "harbor")],
            "odd_words": ["lantern", "microscope", "carrot"],
            "tags": ["geography", "nature"],
        },
        "synonyms": {
            "pairs": [("honest", "truthful"), ("rapid", "swift"), ("frigid", "icy"), ("ancient", "historic")],
            "odd_words": ["suitcase", "teapot", "lantern"],
            "tags": ["vocabulary"],
        },
        "abstract_values": {
            "pairs": [("justice", "fairness"), ("loyalty", "devotion"), ("wisdom", "insight"), ("courage", "bravery")],
            "odd_words": ["mushroom", "toaster", "helmet"],
            "tags": ["abstract"],
        },
        "medicine_forms": {
            "pairs": [("tablet", "capsule"), ("ointment", "gel"), ("syrup", "tonic"), ("bandage", "gauze")],
            "odd_words": ["volcano", "wallet", "ladder"],
            "tags": ["health"],
        },
        "finance_terms": {
            "pairs": [("budget", "saving"), ("credit", "loan"), ("profit", "revenue"), ("invoice", "receipt")],
            "odd_words": ["teacup", "guitar", "blanket"],
            "tags": ["finance"],
        },
        "technology_terms": {
            "pairs": [("server", "router"), ("keyboard", "monitor"), ("browser", "search_engine"), ("tablet", "laptop")],
            "odd_words": ["carrot", "lantern", "cushion"],
            "tags": ["technology"],
        },
        "literature_terms": {
            "pairs": [("novel", "poem"), ("author", "editor"), ("chapter", "prologue"), ("myth", "legend")],
            "odd_words": ["helmet", "wallet", "screwdriver"],
            "tags": ["literature"],
        },
        "biology_terms": {
            "pairs": [("enzyme", "protein"), ("cell", "tissue"), ("leaf", "stem"), ("fungus", "bacteria")],
            "odd_words": ["teapot", "ladder", "blanket"],
            "tags": ["science"],
        },
        "weather_science": {
            "pairs": [("monsoon", "drought"), ("humidity", "pressure"), ("forecast", "climate"), ("cyclone", "tornado")],
            "odd_words": ["wallet", "kettle", "carrot"],
            "tags": ["weather", "science"],
        },
        "government_terms": {
            "pairs": [("senate", "parliament"), ("mayor", "governor"), ("policy", "reform"), ("election", "ballot")],
            "odd_words": ["teacup", "lantern", "pillow"],
            "tags": ["civics"],
        },
    },
    "hard": {
        "advanced_synonyms": {
            "pairs": [("eloquent", "articulate"), ("tenacious", "persistent"), ("placid", "calm"), ("frugal", "economical")],
            "odd_words": ["tractor", "sapphire", "submarine"],
            "tags": ["vocabulary"],
        },
        "advanced_traits": {
            "pairs": [("meticulous", "careful"), ("resilient", "durable"), ("candid", "frank"), ("lucid", "clear")],
            "odd_words": ["asteroid", "helmet", "wheelbarrow"],
            "tags": ["vocabulary"],
        },
        "space_objects": {
            "pairs": [("nebula", "galaxy"), ("asteroid", "comet"), ("quasar", "pulsar"), ("meteor", "satellite")],
            "odd_words": ["ladder", "kettle", "wallet"],
            "tags": ["space"],
        },
        "economics_terms": {
            "pairs": [("equity", "assets"), ("inflation", "deflation"), ("tariff", "subsidy"), ("capital", "liquidity")],
            "odd_words": ["giraffe", "lantern", "pillow"],
            "tags": ["finance", "economics"],
        },
        "geology_terms": {
            "pairs": [("quartz", "basalt"), ("alloy", "ore"), ("magma", "lava"), ("erosion", "sediment")],
            "odd_words": ["parachute", "teacup", "wallet"],
            "tags": ["earth_science"],
        },
        "literary_forms": {
            "pairs": [("sonnet", "haiku"), ("satire", "parody"), ("allegory", "fable"), ("epic", "ballad")],
            "odd_words": ["microscope", "helmet", "carrot"],
            "tags": ["literature"],
        },
        "linguistics_terms": {
            "pairs": [("syntax", "grammar"), ("phoneme", "syllable"), ("prefix", "suffix"), ("dialect", "accent")],
            "odd_words": ["ladder", "wallet", "lantern"],
            "tags": ["language"],
        },
        "law_terms": {
            "pairs": [("verdict", "appeal"), ("statute", "clause"), ("contract", "liability"), ("plaintiff", "defendant")],
            "odd_words": ["teapot", "giraffe", "pillow"],
            "tags": ["law"],
        },
        "philosophy_terms": {
            "pairs": [("ethics", "morality"), ("logic", "reason"), ("belief", "doctrine"), ("paradox", "fallacy")],
            "odd_words": ["screwdriver", "lantern", "blanket"],
            "tags": ["philosophy"],
        },
        "advanced_science": {
            "pairs": [("molecule", "compound"), ("neuron", "synapse"), ("atom", "isotope"), ("catalyst", "reactant")],
            "odd_words": ["wallet", "tractor", "cushion"],
            "tags": ["science"],
        },
        "art_terms": {
            "pairs": [("fresco", "mural"), ("portrait", "landscape"), ("palette", "pigment"), ("sculpture", "bust")],
            "odd_words": ["helmet", "wallet", "teacup"],
            "tags": ["art"],
        },
        "maritime_terms": {
            "pairs": [("harbor", "port"), ("anchor", "mast"), ("deck", "hull"), ("cargo", "freight")],
            "odd_words": ["candle", "pillow", "wallet"],
            "tags": ["travel"],
        },
    },
}


def seed_word_meaning_catalog(apps, schema_editor):
    WordMeaningItem = apps.get_model("assessments", "WordMeaningItem")
    existing_keys = {
        (item.pair_word_1, item.pair_word_2, item.odd_word, item.difficulty)
        for item in WordMeaningItem.objects.all().only("pair_word_1", "pair_word_2", "odd_word", "difficulty")
    }

    rows_to_create = []
    for difficulty, groups in WORD_MEANING_CATALOG.items():
        for relationship_type, config in groups.items():
            tags = config["tags"]
            for pair_word_1, pair_word_2 in config["pairs"]:
                for odd_word in config["odd_words"]:
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
        ("assessments", "0005_expand_wordmeaning_seed"),
    ]

    operations = [
        migrations.RunPython(seed_word_meaning_catalog, migrations.RunPython.noop),
    ]
