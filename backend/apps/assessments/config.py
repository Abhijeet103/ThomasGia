from __future__ import annotations

from backend.apps.assessments.models import SectionType


ASSESSMENT_PREPGIA = "prepgia"
ASSESSMENT_CCAT = "ccat"

ASSESSMENT_CONFIG = {
    ASSESSMENT_PREPGIA: {
        "slug": ASSESSMENT_PREPGIA,
        "title": "Thomas GIA",
        "eyebrow": "Thomas GIA practice platform",
        "description": "Thomas GIA-style speed practice with full tests and section-wise drills.",
        "full_test_title": "Full test",
        "full_test_description": "All five sections in one flow, designed to feel very close to the real GIA.",
        "full_test_meta_tail": "feels like the real GIA",
        "full_test_intro_copy": "Each section is shown one by one. First you get instructions, then eight practice questions with instant feedback, then the timed test for that section.",
        "full_test_practice_count": 8,
        "module_label": "Modules",
        "modules": [
            {
                "key": SectionType.REASONING,
                "title": "Reasoning",
                "description": "Comparative and transitive logic questions under timed conditions.",
                "instruction": "Read the context statements first. Once you understand the relationship, reveal the question and choose the correct person or thing.",
                "time_limit_seconds": 300,
            },
            {
                "key": SectionType.PERCEPTUAL_SPEED,
                "title": "Perceptual Speed",
                "description": "Fast letter-pair matching built to simulate GIA-style pressure.",
                "instruction": "Look at the letter pairs carefully. Count the matching pairs quickly before selecting the correct number.",
                "time_limit_seconds": 120,
            },
            {
                "key": SectionType.NUMBER_SPEED_ACCURACY,
                "title": "Number Speed & Accuracy",
                "description": "Find the number furthest from the median with speed and accuracy.",
                "instruction": "Review the three numbers, identify the middle value mentally, and choose the number furthest from it.",
                "time_limit_seconds": 120,
            },
            {
                "key": SectionType.WORD_MEANING,
                "title": "Word Meaning",
                "description": "Odd-one-out vocabulary sets backed by a curated word bank.",
                "instruction": "Read the words shown in the context, spot the odd one out, and then choose it from the answer options.",
                "time_limit_seconds": 180,
            },
            {
                "key": SectionType.SPATIAL_VISUALIZATION,
                "title": "Spatial Visualization",
                "description": "Decide whether abstract shapes are rotated matches or mirrored variants.",
                "instruction": "Study the shapes first, then decide whether they are the same when rotated or if one is mirrored.",
                "time_limit_seconds": 120,
            },
        ],
    },
    ASSESSMENT_CCAT: {
        "slug": ASSESSMENT_CCAT,
        "title": "CCAT",
        "eyebrow": "CCAT aptitude practice platform",
        "description": "Numerical, verbal, and abstract aptitude practice with module drills and full tests.",
        "full_test_title": "Full test",
        "full_test_description": "Three CCAT-style modules in one focused run: math, verbal, and abstract reasoning.",
        "full_test_meta_tail": "mixed aptitude practice",
        "full_test_intro_copy": "Move through the CCAT-style modules in order. Practice questions come first, followed by the timed test for each module.",
        "full_test_practice_count": 6,
        "module_label": "Modules",
        "modules": [
            {
                "key": SectionType.CCAT_NUMERICAL,
                "title": "Math & Numerical Reasoning",
                "description": "Fast quantitative reasoning with number series, ratios, percentages, and work-rate logic.",
                "instruction": "Read the question, work mentally where possible, and choose the best quantitative answer quickly.",
                "time_limit_seconds": 180,
            },
            {
                "key": SectionType.CCAT_VERBAL,
                "title": "Verbal Reasoning",
                "description": "Analogies, sentence logic, vocabulary, and odd-one-out verbal questions.",
                "instruction": "Read the prompt carefully, compare the options, and choose the strongest language-based answer.",
                "time_limit_seconds": 180,
            },
            {
                "key": SectionType.CCAT_SPATIAL,
                "title": "Spatial & Abstract Reasoning",
                "description": "Pattern recognition, transformations, and non-verbal logic questions.",
                "instruction": "Look for the transformation rule or pattern first, then choose the option that completes it best.",
                "time_limit_seconds": 180,
            },
        ],
    },
}


def get_assessment_config(assessment_type: str) -> dict:
    try:
        return ASSESSMENT_CONFIG[assessment_type]
    except KeyError as exc:
        raise KeyError(f"Unsupported assessment type: {assessment_type}") from exc


def get_assessment_module_keys(assessment_type: str) -> list[str]:
    return [module["key"] for module in get_assessment_config(assessment_type)["modules"]]


def get_module_meta(section_type: str) -> dict:
    for assessment_type, config in ASSESSMENT_CONFIG.items():
        for module in config["modules"]:
            if module["key"] == section_type:
                enriched = dict(module)
                enriched["assessment_type"] = assessment_type
                return enriched
    raise KeyError(f"Unsupported section type: {section_type}")


def get_module_assessment_type(section_type: str) -> str:
    return get_module_meta(section_type)["assessment_type"]


def get_time_limit_seconds(section_type: str) -> int:
    return int(get_module_meta(section_type)["time_limit_seconds"])


def get_assessment_cards() -> list[dict]:
    cards = []
    for key, config in ASSESSMENT_CONFIG.items():
        cards.append(
            {
                "key": key,
                "title": config["title"],
                "description": config["description"],
                "module_count": len(config["modules"]),
            }
        )
    return cards
