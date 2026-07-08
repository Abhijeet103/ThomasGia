from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EXPORT_PATH = Path("data/generated_questions.json")


def read_export() -> dict[str, Any]:
    if not EXPORT_PATH.exists():
        return {"generated_at": None, "questions": []}
    return json.loads(EXPORT_PATH.read_text(encoding="utf-8"))


def get_questions(section_type: str | None = None) -> list[dict[str, Any]]:
    questions = read_export().get("questions", [])
    if section_type is None:
        return questions
    return [item for item in questions if item.get("section_type") == section_type]

