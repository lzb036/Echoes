from __future__ import annotations

import sqlite3
from importlib import resources

from echoes.time_utils import to_iso, utc_now

SCHEMA_VERSION = 4


def migrate(conn: sqlite3.Connection) -> None:
    schema = resources.files("echoes.db").joinpath("schema.sql").read_text(encoding="utf-8")
    with conn:
        if _has_legacy_cards_schema(conn) or _has_legacy_reviews_schema(conn):
            conn.execute("DROP TABLE IF EXISTS reviews")
            conn.execute("DROP TABLE IF EXISTS cards")
        conn.executescript(schema)
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations(version, applied_at)
            VALUES (?, ?)
            """,
            (SCHEMA_VERSION, to_iso(utc_now())),
        )


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def _has_legacy_cards_schema(conn: sqlite3.Connection) -> bool:
    columns = _table_columns(conn, "cards")
    if not columns:
        return False
    return "fsrs_state" in columns or "due_at" in columns or "pass_count" not in columns


def _has_legacy_reviews_schema(conn: sqlite3.Connection) -> bool:
    columns = _table_columns(conn, "reviews")
    if not columns:
        return False
    return (
        "state_before" in columns
        or "scheduled_days" in columns
        or "pass_count_before" not in columns
    )
