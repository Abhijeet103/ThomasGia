from __future__ import annotations

import argparse
import uuid

from prepgia.generators import SECTION_TYPES, generate_question
from prepgia.schema import DEFAULT_DB_PATH, get_connection, init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sample PrepGIA questions into SQLite.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to the SQLite database file.")
    parser.add_argument(
        "--section",
        choices=SECTION_TYPES + ["all"],
        default="all",
        help="Section to generate questions for.",
    )
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="easy")
    parser.add_argument("--count", type=int, default=5, help="Questions per section.")
    parser.add_argument("--label", default="initial-seed", help="Run label for audit tracking.")
    args = parser.parse_args()

    init_db(args.db)
    conn = get_connection(args.db)
    try:
        sections = SECTION_TYPES if args.section == "all" else [args.section]
        inserted = 0

        for section_type in sections:
            for index in range(args.count):
                seed = f"{section_type}-{args.difficulty}-{index}-{uuid.uuid4().hex[:8]}"
                question = generate_question(section_type, args.difficulty, seed, conn=conn)
                conn.execute(
                    """
                    INSERT INTO generated_questions (
                        section_type, seed, difficulty, question_payload_json, correct_answer_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        question.section_type,
                        question.seed,
                        question.difficulty,
                        question.payload_json(),
                        question.correct_answer_json(),
                    ),
                )
                inserted += 1

            conn.execute(
                """
                INSERT INTO generator_runs (run_label, section_type, question_count)
                VALUES (?, ?, ?)
                """,
                (args.label, section_type, args.count),
            )

        conn.commit()
    finally:
        conn.close()

    print(f"Inserted {inserted} questions into {args.db}")


if __name__ == "__main__":
    main()

