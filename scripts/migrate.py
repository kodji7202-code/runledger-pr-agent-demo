#!/usr/bin/env python3
"""Apply pending SQL migrations to the TaskLite database."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import apply_migrations, connect  # noqa: E402


def main():
    path = os.environ.get("TASKLITE_DB", "tasklite.db")
    conn = connect(path)
    try:
        applied = apply_migrations(conn)
    finally:
        conn.close()
    for name in applied:
        print(f"applied {name}")
    if not applied:
        print("database is up to date")


if __name__ == "__main__":
    main()
