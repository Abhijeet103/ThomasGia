from __future__ import annotations

import json
import math
import random
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.apps.assessments.models import WordMeaningItem


SECTION_TYPES = [
    "reasoning",
    "perceptual_speed",
    "number_speed_accuracy",
    "word_meaning",
    "spatial_visualization",
    "ccat_numerical",
    "ccat_verbal",
    "ccat_spatial",
]

TRAITS = [
    "fast",
    "happy",
    "strong",
    "smart",
    "tall",
    "rich",
    "calm",
    "brave",
    "careful",
    "creative",
    "curious",
    "focused",
    "friendly",
    "generous",
    "kind",
    "organized",
    "patient",
    "quick",
    "sharp",
    "steady",
    "alert",
    "ambitious",
    "balanced",
    "cheerful",
    "confident",
    "dependable",
    "diligent",
    "efficient",
    "gentle",
    "honest",
    "inventive",
    "logical",
    "observant",
    "polite",
    "reliable",
    "thoughtful",
]
NAMES = [
    "Tom",
    "Robert",
    "Chloe",
    "Charles",
    "Maya",
    "Noah",
    "Ava",
    "Leo",
    "Emma",
    "Rachel",
    "Aria",
    "Ethan",
    "Ivy",
    "Lucas",
    "Mila",
    "Owen",
    "Sofia",
    "Liam",
    "Zara",
    "Nathan",
    "Ella",
    "Julian",
    "Grace",
    "Henry",
    "Nina",
    "Isaac",
    "Priya",
    "Rohan",
    "Anya",
    "Daniel",
    "Harper",
    "Victor",
    "Aiden",
    "Bella",
    "Caleb",
    "Daisy",
    "Elena",
    "Felix",
    "Gia",
    "Hudson",
    "Jasmine",
    "Kian",
    "Layla",
    "Mason",
    "Nora",
    "Oscar",
    "Pooja",
    "Quinn",
    "Reyansh",
    "Sara",
    "Tara",
    "Uma",
    "Vihaan",
    "Willow",
    "Xavier",
    "Yash",
    "Zane",
]
REASONING_COMPARISON_TEMPLATES = [
    "{left} is more {trait} than {right}.",
    "{left} is less {trait} than {right}.",
    "Compared with {right}, {left} is more {trait}.",
    "Compared with {right}, {left} is less {trait}.",
    "{right} is less {trait} than {left}.",
    "{right} is more {trait} than {left}.",
]
REASONING_QUESTION_TEMPLATES = {
    "most": [
        "Who is the most {trait}?",
        "Which person is more {trait}?",
        "Who appears to be the most {trait}?",
    ],
    "least": [
        "Who is the least {trait}?",
        "Which person is less {trait}?",
        "Who appears to be the least {trait}?",
    ],
}
PERCEPTUAL_SPEED_LETTER_POOLS = {
    "easy": list("ABCDEFGHJKLMNPRSTUVWXYZ"),
    "medium": list("BCDEFGHJKMNPRSTUVWXYZ"),
    "hard": list("bdfghjkmnpqrtxyBDFGHJKMNPQRTXY"),
}
PERCEPTUAL_SPEED_INSTRUCTIONS = [
    "Count how many pairs show the same letter in different case.",
    "How many pairs contain the same letter, once uppercase and once lowercase?",
    "Count the pairs where both letters match apart from case.",
]
WORD_MEANING_INSTRUCTIONS = [
    "Choose the odd one out.",
    "Which word does not belong with the other two?",
    "Pick the word that does not fit the group.",
]
CCAT_SENTENCE_TEMPLATES = [
    "Despite the {descriptor} weather, the outdoor event proceeded as planned.",
    "The manager praised her {descriptor} approach to solving the deadline issue.",
    "His answer sounded {descriptor}, so the team asked for stronger evidence.",
]
CCAT_SENTENCE_OPTIONS = {
    "inclement": ["favorable", "inclement", "predictable", "mild"],
    "methodical": ["careless", "methodical", "random", "casual"],
    "vague": ["precise", "vague", "confident", "detailed"],
}
CCAT_ANALOGIES = [
    ("Doctor", "Patient", "Teacher", ["Classroom", "Student", "Lesson", "School"], "Student"),
    ("Chef", "Kitchen", "Pilot", ["Runway", "Cockpit", "Ticket", "Airport"], "Cockpit"),
    ("Painter", "Brush", "Writer", ["Notebook", "Pen", "Library", "Idea"], "Pen"),
]
CCAT_ODD_ONE_OUT = [
    (["Sprint", "Jog", "Walk", "Whisper"], "Whisper"),
    (["Maple", "Oak", "Pine", "Copper"], "Copper"),
    (["Tablet", "Capsule", "Syrup", "Lantern"], "Lantern"),
]
CCAT_SPATIAL_RULES = [
    {
        "question": "Which option continues the sequence where the shape rotates 90° clockwise each step?",
        "options": ["▲", "▶", "▼", "◀"],
        "answer": "◀",
        "instruction": "Track the direction change from one shape to the next.",
    },
    {
        "question": "Which option is the mirrored version of the reference pattern?",
        "options": ["◧", "◨", "◩", "◪"],
        "answer": "◨",
        "instruction": "Compare the filled side of each figure to the reference rule.",
    },
    {
        "question": "Which option completes the abstract pattern by adding one new side each step?",
        "options": ["△", "□", "⬟", "⬢"],
        "answer": "⬢",
        "instruction": "Count the edges and follow the growth pattern.",
    },
]


@dataclass
class GeneratedQuestion:
    section_type: str
    difficulty: str
    seed: str
    payload: dict
    correct_answer: dict

    def payload_json(self) -> str:
        return json.dumps(self.payload, sort_keys=True)

    def correct_answer_json(self) -> str:
        return json.dumps(self.correct_answer, sort_keys=True)


class BaseQuestionGenerator(ABC):
    section_type: str

    @abstractmethod
    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        raise NotImplementedError

    def rng(self, seed: str) -> random.Random:
        return random.Random(seed)


class ReasoningGenerator(BaseQuestionGenerator):
    section_type = "reasoning"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        entity_count = 2
        names = rng.sample(NAMES, entity_count)
        trait = rng.choice(TRAITS)
        stronger, weaker = rng.sample(names, 2)
        ask_for = rng.choice(["most", "least"])
        answer = stronger if ask_for == "most" else weaker
        statement_template = rng.choice(REASONING_COMPARISON_TEMPLATES)
        if "less" in statement_template:
            if statement_template.startswith("{left}") or "Compared with {right}, {left}" in statement_template:
                left, right = weaker, stronger
            else:
                left, right = stronger, weaker
        else:
            if statement_template.startswith("{left}") or "Compared with {right}, {left}" in statement_template:
                left, right = stronger, weaker
            else:
                left, right = weaker, stronger
        statements = [statement_template.format(left=left, right=right, trait=trait)]
        question = rng.choice(REASONING_QUESTION_TEMPLATES[ask_for]).format(trait=trait)

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "statements": statements,
                "question": question,
            },
            "options": names,
            "metadata": {
                "difficulty": difficulty,
                "trait": trait,
                "comparison_template": statement_template,
            },
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": answer})


class PerceptualSpeedGenerator(BaseQuestionGenerator):
    section_type = "perceptual_speed"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        length = 4 if difficulty == "easy" else 6
        letter_pool = PERCEPTUAL_SPEED_LETTER_POOLS.get(difficulty, PERCEPTUAL_SPEED_LETTER_POOLS["medium"])
        pairs = []
        match_count = 0

        for _ in range(length):
            same = rng.random() < (0.55 if difficulty == "easy" else 0.45)
            left = rng.choice(letter_pool).upper()
            if same:
                right = left.lower()
                match_count += 1
            else:
                different = rng.choice([c.lower() for c in letter_pool if c.lower() != left.lower()])
                right = different
            pairs.append({"left": left, "right": right})

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": rng.choice(PERCEPTUAL_SPEED_INSTRUCTIONS),
                "pairs": pairs,
            },
            "options": list(range(length + 1)),
            "metadata": {
                "difficulty": difficulty,
                "letter_pool_size": len(letter_pool),
            },
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": match_count})


class NumberSpeedAccuracyGenerator(BaseQuestionGenerator):
    section_type = "number_speed_accuracy"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        upper = 50 if difficulty == "easy" else 200

        while True:
            numbers = rng.sample(range(1, upper + 1), 3)
            ordered = sorted(numbers)
            low_gap = ordered[1] - ordered[0]
            high_gap = ordered[2] - ordered[1]
            if low_gap != high_gap:
                break

        if low_gap > high_gap:
            answer = ordered[0]
        else:
            answer = ordered[2]

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": "Which number is furthest from the middle value?",
                "numbers": numbers,
            },
            "options": numbers,
            "metadata": {"difficulty": difficulty},
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": answer})


class WordMeaningGenerator(BaseQuestionGenerator):
    section_type = "word_meaning"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        queryset = WordMeaningItem.objects.filter(is_active=True)
        row = queryset.filter(difficulty=difficulty).order_by("?").first() or queryset.order_by("?").first()
        if row is None:
            raise ValueError("No word meaning items available.")

        words = [row.pair_word_1, row.pair_word_2, row.odd_word]
        rng.shuffle(words)

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": rng.choice(WORD_MEANING_INSTRUCTIONS),
                "words": words,
            },
            "options": words,
            "metadata": {
                "difficulty": difficulty,
                "relationship_type": row.relationship_type,
            },
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": row.odd_word})


class SpatialVisualizationGenerator(BaseQuestionGenerator):
    section_type = "spatial_visualization"
    LETTERS = ["b", "d", "f", "g", "j", "k", "n", "p", "q", "r", "y"]

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        letters = rng.sample(self.LETTERS, 2)
        pairs = []
        match_count = 0
        for letter in letters:
            is_same = rng.choice([True, False])
            if is_same:
                match_count += 1
            pairs.append({"letter": letter, "same": is_same})

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": "How many pairs show the same image?",
                "letter_pairs": pairs,
            },
            "options": ["0", "1", "2"],
            "metadata": {"difficulty": difficulty},
        }
        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            payload,
            {"answer": str(match_count)},
        )


class CCATNumericalGenerator(BaseQuestionGenerator):
    section_type = "ccat_numerical"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        subtype = rng.choice(["series", "discount", "ratio"])

        if subtype == "series":
            start = rng.randint(2, 6)
            gap = rng.randint(2, 5)
            series = [start]
            increment = gap
            for _ in range(4):
                series.append(series[-1] + increment)
                increment += 2
            answer = series[-1] + increment
            options = [answer, answer + 2, answer - 2, answer + 4]
            rng.shuffle(options)
            prompt = {
                "instruction": "What comes next in the number series?",
                "question": f"{', '.join(str(value) for value in series)}, ___",
            }
        elif subtype == "discount":
            base = rng.choice([40, 50, 60, 75, 80])
            markup = rng.choice([20, 25, 40])
            discount = rng.choice([10, 20, 25])
            marked = base * (1 + markup / 100)
            answer = round(marked * (1 - discount / 100), 2)
            options = [answer, round(base * (1 - discount / 100), 2), round(base * (1 + (markup - discount) / 100), 2), round(marked, 2)]
            prompt = {
                "instruction": "Calculate the final price.",
                "question": f"A product costing ${base} is marked up by {markup}% and then discounted by {discount}%. What is the final price?",
            }
        else:
            workers = rng.randint(3, 6)
            days = rng.randint(4, 8)
            target_workers = workers - 1
            answer = round((workers * days) / target_workers, 2)
            options = [answer, round(days - 1, 2), round(days + 1, 2), round((target_workers * days) / workers, 2)]
            prompt = {
                "instruction": "Use work-rate reasoning.",
                "question": f"If {workers} workers can finish a job in {days} days, how many days will {target_workers} workers need?",
            }

        option_strings = [str(option).rstrip("0").rstrip(".") if isinstance(option, float) else str(option) for option in options]
        answer_string = str(answer).rstrip("0").rstrip(".") if isinstance(answer, float) else str(answer)
        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            {
                "question_id": str(uuid.uuid4()),
                "section_type": self.section_type,
                "prompt": prompt,
                "options": option_strings,
                "metadata": {"difficulty": difficulty, "subtype": subtype},
            },
            {"answer": answer_string},
        )


class CCATVerbalGenerator(BaseQuestionGenerator):
    section_type = "ccat_verbal"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        subtype = rng.choice(["analogy", "sentence", "odd_one_out"])

        if subtype == "analogy":
            left, right, target, options, answer = rng.choice(CCAT_ANALOGIES)
            prompt = {
                "instruction": "Choose the option that completes the analogy.",
                "question": f"{left} is to {right} as {target} is to ___?",
            }
        elif subtype == "sentence":
            descriptor = rng.choice(list(CCAT_SENTENCE_OPTIONS.keys()))
            options = CCAT_SENTENCE_OPTIONS[descriptor][:]
            template = rng.choice(CCAT_SENTENCE_TEMPLATES)
            answer = descriptor
            prompt = {
                "instruction": "Choose the word that best completes the sentence.",
                "question": template.format(descriptor="_____"),
            }
        else:
            options, answer = rng.choice(CCAT_ODD_ONE_OUT)
            prompt = {
                "instruction": "Choose the word that does not belong.",
                "question": "Which word does not belong with the others?",
            }

        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            {
                "question_id": str(uuid.uuid4()),
                "section_type": self.section_type,
                "prompt": prompt,
                "options": options,
                "metadata": {"difficulty": difficulty, "subtype": subtype},
            },
            {"answer": answer},
        )


class CCATSpatialGenerator(BaseQuestionGenerator):
    section_type = "ccat_spatial"

    def generate(self, difficulty: str, seed: str, conn=None) -> GeneratedQuestion:
        rng = self.rng(seed)
        rule = rng.choice(CCAT_SPATIAL_RULES)
        return GeneratedQuestion(
            self.section_type,
            difficulty,
            seed,
            {
                "question_id": str(uuid.uuid4()),
                "section_type": self.section_type,
                "prompt": {
                    "instruction": rule["instruction"],
                    "question": rule["question"],
                },
                "options": rule["options"],
                "metadata": {"difficulty": difficulty, "subtype": "abstract_pattern"},
            },
            {"answer": rule["answer"]},
        )


def _make_polygon_points(rng: random.Random, vertex_count: int) -> list[list[float]]:
    points = []
    for index in range(vertex_count):
        angle = (2 * math.pi * index) / vertex_count
        radius = rng.uniform(25, 45)
        x = round(math.cos(angle) * radius, 2)
        y = round(math.sin(angle) * radius * rng.uniform(0.7, 1.2), 2)
        points.append([x, y])
    return points


GENERATOR_MAP = {
    "reasoning": ReasoningGenerator(),
    "perceptual_speed": PerceptualSpeedGenerator(),
    "number_speed_accuracy": NumberSpeedAccuracyGenerator(),
    "word_meaning": WordMeaningGenerator(),
    "spatial_visualization": SpatialVisualizationGenerator(),
    "ccat_numerical": CCATNumericalGenerator(),
    "ccat_verbal": CCATVerbalGenerator(),
    "ccat_spatial": CCATSpatialGenerator(),
}


def generate_question(
    section_type: str,
    difficulty: str,
    seed: str,
    conn=None,
) -> GeneratedQuestion:
    try:
        generator = GENERATOR_MAP[section_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported section type: {section_type}") from exc
    return generator.generate(difficulty=difficulty, seed=seed, conn=conn)
