from __future__ import annotations

import sqlite3
from importlib import resources

from echoes.time_utils import to_iso, utc_now

SCHEMA_VERSION = 2


def migrate(conn: sqlite3.Connection) -> None:
    schema = resources.files("echoes.db").joinpath("schema.sql").read_text(encoding="utf-8")
    with conn:
        conn.executescript(schema)
        _ensure_column(conn, "cards", "pass_count", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "cards", "completed_at", "TEXT")
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations(version, applied_at)
            VALUES (?, ?)
            """,
            (SCHEMA_VERSION, to_iso(utc_now())),
        )


def _ensure_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
