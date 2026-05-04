from __future__ import annotations

import sqlite3
from importlib import resources

from echoes.time_utils import to_iso, utc_now

SCHEMA_VERSION = 1


def migrate(conn: sqlite3.Connection) -> None:
    schema = resources.files("echoes.db").joinpath("schema.sql").read_text(encoding="utf-8")
    with conn:
        conn.executescript(schema)
        conn.execute(
            """
            INSERT OR IGNORE INTO schema_migrations(version, applied_at)
            VALUES (?, ?)
            """,
            (SCHEMA_VERSION, to_iso(utc_now())),
        )
