"""
schema.py

Defines and creates the SQLite schema for the Notebook app.

Run this once before starting the server:
    python schema.py

It's safe to re-run — tables are only created if they don't already
exist. server.py also calls init_db() on startup as a safety net, so
this script mainly exists to let you inspect/create the schema on its
own, separately from the API code.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "notebook.db"


def get_connection() -> sqlite3.Connection:
    """Open a connection to the notebook database.

    SQLite has foreign keys off by default per-connection, so we turn
    them on every time. row_factory lets us access columns by name
    (row["username"]) instead of by index.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# One row per registered account.
USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# One row per user (UNIQUE user_id) — this is a single-note app, not a
# list of notes. Saving always overwrites the user's one note.
NOTES_TABLE = """
CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL UNIQUE,
    content    TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
"""


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(USERS_TABLE)
        conn.execute(NOTES_TABLE)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DB_PATH}")
