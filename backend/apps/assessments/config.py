from __future__ import annotations

from backend.apps.assessments.models import SectionType


ASSESSMENT_PREPGIA = "prepgia"
ASSESSMENT_CCAT = "ccat"
ASSESSMENT_WATSON_GLASER = "watson_glaser"
ASSESSMENT_SHL_VERIFY = "shl_verify"

ASSESSMENT_CONFIG = {
    ASSESSMENT_PREPGIA: {
        "slug": ASSESSMENT_PREPGIA,
        "title": "Thomas GIA",
        "eyebrow": "Thomas GIA practice platform",
        "description": "Thomas GIA-style speed practice with full tests and section-wise drills.",
        "full_test_title": "Full test",
        "full_test_description": "All five sections in one flow, designed to feel very close to the real GIA.",
        "full_test_meta_tail": "",
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
                "help": {
                    "task": "Remember a comparison, then answer a question about the relationship without seeing the original statement.",
                    "steps": [
                        "Identify the people or things being compared.",
                        "Restate the comparison in simpler words.",
                        "Keep the direction of the relationship clear when the question appears.",
                    ],
                    "watch_out": "Reversed or negative wording such as less careful instead of more careful.",
                    "tip": "Mentally place the stronger or greater item first before revealing the question.",
                },
            },
            {
                "key": SectionType.PERCEPTUAL_SPEED,
                "title": "Perceptual Speed",
                "description": "Fast letter-pair matching built to simulate GIA-style pressure.",
                "instruction": "Look at the letter pairs carefully. Count the matching pairs quickly before selecting the correct number.",
                "time_limit_seconds": 120,
                "help": {
                    "task": "Compare the letter pairs and count how many are exact matches.",
                    "steps": [
                        "Scan the pairs from left to right.",
                        "Compare both characters in each pair.",
                        "Keep a running count and answer once the row is complete.",
                    ],
                    "watch_out": "Do not count a pair when only one of its characters matches.",
                    "tip": "Use a steady scan rhythm instead of repeatedly checking earlier pairs.",
                },
            },
            {
                "key": SectionType.NUMBER_SPEED_ACCURACY,
                "title": "Number Speed & Accuracy",
                "description": "Find the number furthest from the median with speed and accuracy.",
                "instruction": "Review the three numbers, identify the middle value mentally, and choose the number furthest from it.",
                "time_limit_seconds": 120,
                "help": {
                    "task": "Find the middle value, then choose the number furthest away from it.",
                    "steps": [
                        "Order the three values from smallest to largest.",
                        "Identify the middle value.",
                        "Compare the distance from the middle to both outer values.",
                    ],
                    "watch_out": "The correct answer is not always the largest number.",
                    "tip": "Ignore the middle value after identifying it and compare only the two gaps.",
                },
            },
            {
                "key": SectionType.WORD_MEANING,
                "title": "Word Meaning",
                "description": "Odd-one-out vocabulary sets backed by a curated word bank.",
                "instruction": "Read the words shown in the context, spot the odd one out, and then choose it from the answer options.",
                "time_limit_seconds": 180,
                "help": {
                    "task": "Identify the word that does not belong with the others.",
                    "steps": [
                        "Look for a meaning or category shared by most words.",
                        "Test each word against that shared relationship.",
                        "Choose the word that falls outside the group.",
                    ],
                    "watch_out": "Do not choose a word only because it is less familiar.",
                    "tip": "Describe the shared group in one short phrase before selecting the odd word.",
                },
            },
            {
                "key": SectionType.SPATIAL_VISUALIZATION,
                "title": "Spatial Visualization",
                "description": "Decide whether abstract shapes are rotated matches or mirrored variants.",
                "instruction": "Study the shapes first, then decide whether they are the same when rotated or if one is mirrored.",
                "time_limit_seconds": 120,
                "help": {
                    "task": "Decide whether two shapes are the same after rotation or whether one has been mirrored.",
                    "steps": [
                        "Choose one distinctive corner, mark, or feature.",
                        "Mentally rotate the first shape to align that feature.",
                        "Check whether the remaining features keep the same arrangement.",
                    ],
                    "watch_out": "A mirrored shape cannot be matched by rotation alone.",
                    "tip": "Track an asymmetric feature rather than comparing the whole outline at once.",
                },
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
                "help": {
                    "task": "Solve short numerical problems involving patterns, ratios, percentages, and practical arithmetic.",
                    "steps": [
                        "Identify the type of calculation the question requires.",
                        "Estimate the likely answer range.",
                        "Calculate only what is needed and eliminate unsuitable options.",
                    ],
                    "watch_out": "Avoid spending time on exact calculation when estimation separates the options.",
                    "tip": "Check units and direction before calculating.",
                },
            },
            {
                "key": SectionType.CCAT_VERBAL,
                "title": "Verbal Reasoning",
                "description": "Analogies, sentence logic, vocabulary, and odd-one-out verbal questions.",
                "instruction": "Read the prompt carefully, compare the options, and choose the strongest language-based answer.",
                "time_limit_seconds": 180,
                "help": {
                    "task": "Solve analogies, vocabulary, sentence logic, and word-group questions.",
                    "steps": [
                        "Identify the relationship or language rule being tested.",
                        "Predict the kind of answer you expect.",
                        "Compare that prediction with the available options.",
                    ],
                    "watch_out": "A plausible option may still fail to match the exact relationship.",
                    "tip": "State an analogy relationship as a short sentence before checking the answers.",
                },
            },
            {
                "key": SectionType.CCAT_SPATIAL,
                "title": "Spatial & Abstract Reasoning",
                "description": "Pattern recognition, transformations, and non-verbal logic questions.",
                "instruction": "Look for the transformation rule or pattern first, then choose the option that completes it best.",
                "time_limit_seconds": 180,
                "help": {
                    "task": "Identify a visual rule and choose the option that correctly continues or completes it.",
                    "steps": [
                        "Track changes in position, rotation, count, fill, and shape separately.",
                        "Form the simplest rule that explains the sequence.",
                        "Confirm that rule across every available step.",
                    ],
                    "watch_out": "Do not accept a rule that explains only the final two images.",
                    "tip": "Test one visual property at a time before combining multiple changes.",
                },
            },
        ],
    },
}

PRACTICE_TRACK_LIBRARY = {
    ASSESSMENT_PREPGIA: {
        "key": ASSESSMENT_PREPGIA,
        "title": "Thomas GIA",
        "description": "Thomas GIA-style speed practice with full tests and section-wise drills.",
        "module_count": len(ASSESSMENT_CONFIG[ASSESSMENT_PREPGIA]["modules"]),
        "trust_line": "Used by 30,000+ employers across the UK and Europe",
        "available_languages": ["English", "Deutsch — kommt bald"],
        "route_enabled": True,
        "default_visibility_state": "accessible",
    },
    ASSESSMENT_CCAT: {
        "key": ASSESSMENT_CCAT,
        "title": "CCAT",
        "description": "Numerical, verbal, and abstract aptitude practice with module drills and full tests.",
        "module_count": len(ASSESSMENT_CONFIG[ASSESSMENT_CCAT]["modules"]),
        "trust_line": "Taken 10M+ times at 4,500+ US employers",
        "available_languages": ["English"],
        "route_enabled": True,
        "default_visibility_state": "accessible",
    },
    ASSESSMENT_WATSON_GLASER: {
        "key": ASSESSMENT_WATSON_GLASER,
        "title": "Watson-Glaser",
        "description": "Critical reasoning practice covering inference, assumptions, and argument evaluation.",
        "module_count": 4,
        "trust_line": "In testing with a small group right now",
        "available_languages": ["English"],
        "route_enabled": False,
        "default_visibility_state": "upcoming",
    },
    ASSESSMENT_SHL_VERIFY: {
        "key": ASSESSMENT_SHL_VERIFY,
        "title": "SHL Verify",
        "description": "Numerical, verbal, and inductive reasoning practice in the SHL question style.",
        "module_count": 4,
        "trust_line": "In testing with a small group right now",
        "available_languages": ["English"],
        "route_enabled": False,
        "default_visibility_state": "upcoming",
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
    for key, config in PRACTICE_TRACK_LIBRARY.items():
        cards.append(
            {
                "key": key,
                **config,
            }
        )
    return cards
