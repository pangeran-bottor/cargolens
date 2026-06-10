"""Read-only SQLite access. The dataset is seeded once at startup; every
query connection is opened in read-only mode so the API cannot mutate data
(spec: "treat all data as read-only")."""

import sqlite3

from .seed import DB_PATH, seed


def ensure_seeded() -> None:
    if not DB_PATH.exists():
        seed()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn
