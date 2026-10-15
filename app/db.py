import sqlite3
from pathlib import Path

from flask import current_app, g

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def apply_migrations(conn, migrations_dir=MIGRATIONS_DIR):
    """Apply pending *.sql files in name order; return the names applied."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " name TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')))"
    )
    done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
    applied = []
    for path in sorted(Path(migrations_dir).glob("*.sql")):
        if path.name in done:
            continue
        # executescript commits implicitly, so record the migration in the same script
        # to keep "applied" and "recorded" together.
        script = path.read_text()
        conn.executescript(
            "BEGIN;\n"
            f"{script}\n"
            f"INSERT INTO schema_migrations (name) VALUES ('{path.name}');\n"
            "COMMIT;"
        )
        applied.append(path.name)
    return applied


def init_app(app):
    app.teardown_appcontext(close_db)
