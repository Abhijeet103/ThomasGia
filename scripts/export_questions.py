from __future__ import annotations

import argparse
import json
from datetime import datetime, UTC
from pathlib import Path

from prepgia.schema import DEFAULT_DB_PATH, get_connection, init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Export generated SQLite questions to JSON for the Next.js app.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to the SQLite database file.")
    parser.add_argument(
        "--output",
        default="data/generated_questions.json",
        help="Path to the exported JSON file.",
    )
    args = parser.parse_args()

    init_db(args.db)
    conn = get_connection(args.db)
    try:
        rows = conn.execute(
            """
            SELECT id, section_type, seed, difficulty, question_payload_json, correct_answer_json, created_at
            FROM generated_questions
            ORDER BY id ASC
            """
        ).fetchall()
    finally:
        conn.close()

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "questions": [dict(row) for row in rows],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Exported {len(rows)} questions to {output_path}")


if __name__ == "__main__":
    main()

