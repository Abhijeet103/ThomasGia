from __future__ import annotations

import argparse

from prepgia.schema import DEFAULT_DB_PATH, init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the PrepGIA SQLite database.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to the SQLite database file.")
    args = parser.parse_args()

    db_path = init_db(args.db)
    print(f"Initialized database at {db_path}")


if __name__ == "__main__":
    main()

