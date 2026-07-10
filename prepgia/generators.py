from __future__ import annotations

import json
import math
import random
import sqlite3
import string
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


SECTION_TYPES = [
    "reasoning",
    "perceptual_speed",
    "number_speed_accuracy",
    "word_meaning",
    "spatial_visualization",
]

TRAITS = ["fast", "happy", "strong", "smart", "tall", "rich"]
NAMES = ["Tom", "Robert", "Chloe", "Charles", "Maya", "Noah", "Ava", "Leo"]


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
    def generate(self, difficulty: str, seed: str, conn: sqlite3.Connection | None = None) -> GeneratedQuestion:
        raise NotImplementedError

    def rng(self, seed: str) -> random.Random:
        return random.Random(seed)


class ReasoningGenerator(BaseQuestionGenerator):
    section_type = "reasoning"

    def generate(self, difficulty: str, seed: str, conn: sqlite3.Connection | None = None) -> GeneratedQuestion:
        rng = self.rng(seed)
        entity_count = 2
        names = rng.sample(NAMES, entity_count)
        trait = rng.choice(TRAITS)
        ordered = names[:]
        rng.shuffle(ordered)
        statements = [f"{ordered[i]} is more {trait} than {ordered[i + 1]}." for i in range(entity_count - 1)]
        ask_for = rng.choice(["most", "least"])
        answer = ordered[0] if ask_for == "most" else ordered[-1]

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "statements": statements,
                "question": f"Who is the {ask_for} {trait}?",
            },
            "options": names,
            "metadata": {"difficulty": difficulty, "trait": trait},
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": answer})


class PerceptualSpeedGenerator(BaseQuestionGenerator):
    section_type = "perceptual_speed"

    def generate(self, difficulty: str, seed: str, conn: sqlite3.Connection | None = None) -> GeneratedQuestion:
        rng = self.rng(seed)
        length = 4 if difficulty == "easy" else 6
        pairs = []
        match_count = 0

        for _ in range(length):
            same = rng.random() < (0.55 if difficulty == "easy" else 0.45)
            left = rng.choice(string.ascii_uppercase)
            if same:
                right = left.lower()
                match_count += 1
            else:
                different = rng.choice([c for c in string.ascii_lowercase if c != left.lower()])
                right = different
            pairs.append({"left": left, "right": right})

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": "Count how many pairs show the same letter in different case.",
                "pairs": pairs,
            },
            "options": list(range(length + 1)),
            "metadata": {"difficulty": difficulty},
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": match_count})


class NumberSpeedAccuracyGenerator(BaseQuestionGenerator):
    section_type = "number_speed_accuracy"

    def generate(self, difficulty: str, seed: str, conn: sqlite3.Connection | None = None) -> GeneratedQuestion:
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

    def generate(self, difficulty: str, seed: str, conn: sqlite3.Connection | None = None) -> GeneratedQuestion:
        if conn is None:
            raise ValueError("WordMeaningGenerator requires a database connection.")

        rng = self.rng(seed)
        row = conn.execute(
            """
            SELECT * FROM word_meaning_items
            WHERE difficulty = ? AND is_active = 1
            ORDER BY RANDOM()
            LIMIT 1
            """,
            (difficulty,),
        ).fetchone()

        if row is None:
            row = conn.execute(
                "SELECT * FROM word_meaning_items WHERE is_active = 1 ORDER BY RANDOM() LIMIT 1"
            ).fetchone()
        if row is None:
            raise ValueError("No word meaning items available.")

        words = [row["pair_word_1"], row["pair_word_2"], row["odd_word"]]
        rng.shuffle(words)

        payload = {
            "question_id": str(uuid.uuid4()),
            "section_type": self.section_type,
            "prompt": {
                "instruction": "Choose the odd one out.",
                "words": words,
            },
            "options": words,
            "metadata": {
                "difficulty": difficulty,
                "relationship_type": row["relationship_type"],
            },
        }
        return GeneratedQuestion(self.section_type, difficulty, seed, payload, {"answer": row["odd_word"]})


class SpatialVisualizationGenerator(BaseQuestionGenerator):
    section_type = "spatial_visualization"
    LETTERS = ["b", "d", "f", "g", "j", "k", "n", "p", "q", "r", "y"]

    def generate(self, difficulty: str, seed: str, conn: sqlite3.Connection | None = None) -> GeneratedQuestion:
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
}


def generate_question(
    section_type: str,
    difficulty: str,
    seed: str,
    conn: sqlite3.Connection | None = None,
) -> GeneratedQuestion:
    try:
        generator = GENERATOR_MAP[section_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported section type: {section_type}") from exc
    return generator.generate(difficulty=difficulty, seed=seed, conn=conn)

