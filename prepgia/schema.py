from __future__ import annotations

import os
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(os.getenv("QUESTION_BANK_DB_PATH", "data/prepgia.sqlite3"))


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'free',
    auth_provider TEXT,
    auth_provider_user_id TEXT,
    google_sub TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    plan_code TEXT NOT NULL,
    status TEXT NOT NULL,
    current_period_start TEXT,
    current_period_end TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    overall_adjusted_score REAL DEFAULT 0,
    overall_percentile_band TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS attempt_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL,
    section_type TEXT NOT NULL,
    seed TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    time_limit_seconds INTEGER NOT NULL,
    adjusted_score REAL DEFAULT 0,
    percentile_band TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (attempt_id) REFERENCES attempts(id)
);

CREATE TABLE IF NOT EXISTS attempt_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_section_id INTEGER NOT NULL,
    question_index INTEGER NOT NULL,
    question_payload_json TEXT NOT NULL,
    user_answer_json TEXT,
    correct_answer_json TEXT NOT NULL,
    is_correct INTEGER,
    penalty_applied REAL DEFAULT 0,
    response_time_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (attempt_section_id) REFERENCES attempt_sections(id)
);

CREATE TABLE IF NOT EXISTS word_meaning_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair_word_1 TEXT NOT NULL,
    pair_word_2 TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    odd_word TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generated_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_type TEXT NOT NULL,
    seed TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    question_payload_json TEXT NOT NULL,
    correct_answer_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generator_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_label TEXT NOT NULL,
    section_type TEXT,
    question_count INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_generated_questions_section
ON generated_questions(section_type, difficulty);

CREATE INDEX IF NOT EXISTS idx_word_meaning_difficulty
ON word_meaning_items(difficulty, is_active);
"""


WORD_MEANING_SEED = [
    ("dawn", "dusk", "times_of_day", "hammer", "easy", '["time", "nature"]'),
    ("cat", "dog", "animals", "ladder", "easy", '["animal"]'),
    ("violin", "piano", "instruments", "carrot", "easy", '["music"]'),
    ("orbit", "rotate", "space_motion", "blanket", "medium", '["space", "motion"]'),
    ("opaque", "transparent", "material_property", "jungle", "medium", '["science"]'),
    ("triangle", "square", "shapes", "justice", "easy", '["geometry"]'),
    ("mercury", "venus", "planets", "teapot", "easy", '["space"]'),
    ("frugal", "thrifty", "synonyms", "volcano", "hard", '["vocabulary"]'),
    ("elated", "joyful", "synonyms", "compass", "medium", '["emotion"]'),
    ("autumn", "spring", "seasons", "pillow", "easy", '["nature"]'),
]


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> Path:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        _apply_runtime_migrations(conn)
        _seed_word_meaning_items(conn)
        conn.commit()
    finally:
        conn.close()
    return Path(db_path)


def _seed_word_meaning_items(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) AS count FROM word_meaning_items").fetchone()["count"]
    if existing:
        return

    conn.executemany(
        """
        INSERT INTO word_meaning_items (
            pair_word_1, pair_word_2, relationship_type, odd_word, difficulty, tags_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        WORD_MEANING_SEED,
    )


def _apply_runtime_migrations(conn: sqlite3.Connection) -> None:
    _ensure_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'free'")
    _ensure_column(conn, "users", "google_sub", "TEXT")


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
