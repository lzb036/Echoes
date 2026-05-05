from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from echoes.config import DEFAULT_SETTINGS
from echoes.models import CardRecord, DueCard, ReviewStats, Word
from echoes.srs.service import ReviewOutcome as SrsReviewOutcome
from echoes.time_utils import from_iso, to_iso, utc_now


@dataclass(frozen=True)
class WordImportRow:
    term: str
    definition: str = ""
    phonetic: str = ""
    example: str = ""
    note: str = ""
    tags: list[str] | None = None
    source: str = ""


@dataclass(frozen=True)
class RebuildBatchOutcome:
    words_created: int
    cards_created: int
    reviews_deleted: int
    cards_deleted: int
    words_deleted: int


class EchoesStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def seed_default_settings(self) -> None:
        now = to_iso(utc_now())
        with self.conn:
            self.conn.executemany(
                """
                INSERT OR IGNORE INTO settings(key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                [(key, value, now) for key, value in DEFAULT_SETTINGS.items()],
            )

    def get_settings(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def set_setting(self, key: str, value: str) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO settings(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, to_iso(utc_now())),
            )

    def find_word_by_term(self, term: str) -> Word | None:
        row = self.conn.execute(
            """
            SELECT * FROM words
            WHERE lower(term) = lower(?) AND archived_at IS NULL
            LIMIT 1
            """,
            (term.strip(),),
        ).fetchone()
        return _word_from_row(row) if row else None

    def create_word(
        self,
        *,
        term: str,
        definition: str = "",
        phonetic: str = "",
        example: str = "",
        note: str = "",
        tags: list[str] | None = None,
        source: str = "",
        now: datetime | None = None,
    ) -> Word:
        timestamp = now or utc_now()
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO words(
                    term, definition, phonetic, example, note, tags, source, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    term.strip(),
                    definition.strip(),
                    phonetic.strip(),
                    example.strip(),
                    note.strip(),
                    tags_json,
                    source.strip(),
                    to_iso(timestamp),
                    to_iso(timestamp),
                ),
            )
        created = self.get_word(int(cursor.lastrowid))
        if created is None:
            raise RuntimeError("failed to create item")
        return created

    def ensure_word(
        self,
        *,
        term: str,
        definition: str = "",
        phonetic: str = "",
        example: str = "",
        note: str = "",
        tags: list[str] | None = None,
        source: str = "",
    ) -> tuple[Word, bool]:
        existing = self.find_word_by_term(term)
        if existing:
            return existing, False
        return (
            self.create_word(
                term=term,
                definition=definition,
                phonetic=phonetic,
                example=example,
                note=note,
                tags=tags,
                source=source,
            ),
            True,
        )

    def rebuild_word_batch(
        self,
        *,
        words: Sequence[WordImportRow],
        card_type: str,
        card_states: Sequence[tuple[str, datetime]],
        now: datetime | None = None,
    ) -> RebuildBatchOutcome:
        if len(words) != len(card_states):
            raise ValueError("word and card state counts differ")
        if not words:
            raise ValueError("no valid items to import")

        timestamp = now or utc_now()
        timestamp_iso = to_iso(timestamp)
        with self.conn:
            reviews_deleted = self.conn.execute("DELETE FROM reviews").rowcount
            cards_deleted = self.conn.execute("DELETE FROM cards").rowcount
            words_deleted = self.conn.execute("DELETE FROM words").rowcount

            for word, (fsrs_state, due_at) in zip(words, card_states, strict=True):
                word_id = self._insert_word(word, timestamp=timestamp)
                self.conn.execute(
                    """
                    INSERT INTO cards(
                        word_id, card_type, fsrs_state, due_at, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        word_id,
                        card_type,
                        fsrs_state,
                        to_iso(due_at),
                        timestamp_iso,
                        timestamp_iso,
                    ),
                )

        return RebuildBatchOutcome(
            words_created=len(words),
            cards_created=len(words),
            reviews_deleted=reviews_deleted,
            cards_deleted=cards_deleted,
            words_deleted=words_deleted,
        )

    def _insert_word(self, word: WordImportRow, *, timestamp: datetime) -> int:
        tags_json = json.dumps(word.tags or [], ensure_ascii=False)
        cursor = self.conn.execute(
            """
            INSERT INTO words(
                term, definition, phonetic, example, note, tags, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                word.term.strip(),
                word.definition.strip(),
                word.phonetic.strip(),
                word.example.strip(),
                word.note.strip(),
                tags_json,
                word.source.strip(),
                to_iso(timestamp),
                to_iso(timestamp),
            ),
        )
        return int(cursor.lastrowid)

    def get_word(self, word_id: int) -> Word | None:
        row = self.conn.execute("SELECT * FROM words WHERE id = ?", (word_id,)).fetchone()
        return _word_from_row(row) if row else None

    def find_card(self, word_id: int, card_type: str) -> CardRecord | None:
        row = self.conn.execute(
            "SELECT * FROM cards WHERE word_id = ? AND card_type = ?",
            (word_id, card_type),
        ).fetchone()
        return _card_from_row(row) if row else None

    def create_card(
        self,
        *,
        word_id: int,
        card_type: str,
        fsrs_state: str,
        due_at: datetime,
        now: datetime | None = None,
    ) -> CardRecord:
        timestamp = now or utc_now()
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO cards(
                    word_id, card_type, fsrs_state, due_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    word_id,
                    card_type,
                    fsrs_state,
                    to_iso(due_at),
                    to_iso(timestamp),
                    to_iso(timestamp),
                ),
            )
        created = self.get_card(int(cursor.lastrowid))
        if created is None:
            raise RuntimeError("failed to create card")
        return created

    def ensure_card(
        self,
        *,
        word_id: int,
        card_type: str,
        fsrs_state: str,
        due_at: datetime,
    ) -> tuple[CardRecord, bool]:
        existing = self.find_card(word_id, card_type)
        if existing:
            return existing, False
        return (
            self.create_card(
                word_id=word_id,
                card_type=card_type,
                fsrs_state=fsrs_state,
                due_at=due_at,
            ),
            True,
        )

    def get_card(self, card_id: int) -> CardRecord | None:
        row = self.conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        return _card_from_row(row) if row else None

    def next_due_card(self, *, now: datetime | None = None) -> DueCard | None:
        timestamp = to_iso(now or utc_now())
        row = self.conn.execute(
            """
            SELECT
                c.id AS c_id,
                c.word_id AS c_word_id,
                c.card_type AS c_card_type,
                c.fsrs_state AS c_fsrs_state,
                c.due_at AS c_due_at,
                c.last_reviewed_at AS c_last_reviewed_at,
                c.review_count AS c_review_count,
                c.lapse_count AS c_lapse_count,
                c.created_at AS c_created_at,
                c.updated_at AS c_updated_at,
                w.id AS w_id,
                w.term AS w_term,
                w.definition AS w_definition,
                w.phonetic AS w_phonetic,
                w.example AS w_example,
                w.note AS w_note,
                w.tags AS w_tags,
                w.source AS w_source,
                w.created_at AS w_created_at,
                w.updated_at AS w_updated_at,
                w.archived_at AS w_archived_at
            FROM cards c
            JOIN words w ON w.id = c.word_id
            WHERE c.due_at <= ? AND w.archived_at IS NULL
            ORDER BY c.due_at ASC, c.id ASC
            LIMIT 1
            """,
            (timestamp,),
        ).fetchone()
        if row is None:
            return None
        return DueCard(card=_card_from_prefixed_row(row), word=_word_from_prefixed_row(row))

    def apply_review(
        self,
        card_id: int,
        outcome: SrsReviewOutcome,
        *,
        is_manual: bool = False,
    ) -> None:
        with self.conn:
            self.conn.execute(
                """
                UPDATE cards
                SET
                    fsrs_state = ?,
                    due_at = ?,
                    last_reviewed_at = ?,
                    review_count = review_count + 1,
                    lapse_count = lapse_count + ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    outcome.state_after,
                    to_iso(outcome.due_at),
                    to_iso(outcome.reviewed_at),
                    outcome.lapse_delta,
                    to_iso(utc_now()),
                    card_id,
                ),
            )
            self.conn.execute(
                """
                INSERT INTO reviews(
                    card_id, rating, reviewed_at, elapsed_ms, scheduled_days,
                    state_before, state_after, is_manual
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card_id,
                    int(outcome.rating),
                    to_iso(outcome.reviewed_at),
                    outcome.elapsed_ms,
                    outcome.scheduled_days,
                    outcome.state_before,
                    outcome.state_after,
                    1 if is_manual else 0,
                ),
            )

    def count_words(self) -> int:
        return int(
            self.conn.execute(
                "SELECT COUNT(*) AS count FROM words WHERE archived_at IS NULL"
            ).fetchone()["count"]
        )

    def count_cards(self) -> int:
        return int(
            self.conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM cards c
                JOIN words w ON w.id = c.word_id
                WHERE w.archived_at IS NULL
                """
            ).fetchone()["count"]
        )

    def count_due_cards(self, *, now: datetime | None = None) -> int:
        return int(
            self.conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM cards c
                JOIN words w ON w.id = c.word_id
                WHERE c.due_at <= ? AND w.archived_at IS NULL
                """,
                (to_iso(now or utc_now()),),
            ).fetchone()["count"]
        )

    def count_reviews(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) AS count FROM reviews").fetchone()["count"])

    def review_stats(self, *, now: datetime | None = None) -> ReviewStats:
        timestamp = to_iso(now or utc_now())
        row = self.conn.execute(
            """
            SELECT
                COUNT(*) AS total_cards,
                SUM(CASE WHEN c.review_count > 0 THEN 1 ELSE 0 END) AS reviewed_cards,
                SUM(CASE WHEN c.due_at <= ? THEN 1 ELSE 0 END) AS due_cards
            FROM cards c
            JOIN words w ON w.id = c.word_id
            WHERE w.archived_at IS NULL
            """,
            (timestamp,),
        ).fetchone()
        return ReviewStats(
            total_cards=int(row["total_cards"] or 0),
            reviewed_cards=int(row["reviewed_cards"] or 0),
            due_cards=int(row["due_cards"] or 0),
        )


def _word_from_row(row: sqlite3.Row) -> Word:
    return Word(
        id=int(row["id"]),
        term=row["term"],
        definition=row["definition"],
        phonetic=row["phonetic"],
        example=row["example"],
        note=row["note"],
        tags=json.loads(row["tags"]),
        source=row["source"],
        created_at=from_iso(row["created_at"]),
        updated_at=from_iso(row["updated_at"]),
        archived_at=from_iso(row["archived_at"]) if row["archived_at"] else None,
    )


def _card_from_row(row: sqlite3.Row) -> CardRecord:
    return CardRecord(
        id=int(row["id"]),
        word_id=int(row["word_id"]),
        card_type=row["card_type"],
        fsrs_state=row["fsrs_state"],
        due_at=from_iso(row["due_at"]),
        last_reviewed_at=from_iso(row["last_reviewed_at"]) if row["last_reviewed_at"] else None,
        review_count=int(row["review_count"]),
        lapse_count=int(row["lapse_count"]),
        created_at=from_iso(row["created_at"]),
        updated_at=from_iso(row["updated_at"]),
    )


def _word_from_prefixed_row(row: sqlite3.Row) -> Word:
    return Word(
        id=int(row["w_id"]),
        term=row["w_term"],
        definition=row["w_definition"],
        phonetic=row["w_phonetic"],
        example=row["w_example"],
        note=row["w_note"],
        tags=json.loads(row["w_tags"]),
        source=row["w_source"],
        created_at=from_iso(row["w_created_at"]),
        updated_at=from_iso(row["w_updated_at"]),
        archived_at=from_iso(row["w_archived_at"]) if row["w_archived_at"] else None,
    )


def _card_from_prefixed_row(row: sqlite3.Row) -> CardRecord:
    return CardRecord(
        id=int(row["c_id"]),
        word_id=int(row["c_word_id"]),
        card_type=row["c_card_type"],
        fsrs_state=row["c_fsrs_state"],
        due_at=from_iso(row["c_due_at"]),
        last_reviewed_at=from_iso(row["c_last_reviewed_at"]) if row["c_last_reviewed_at"] else None,
        review_count=int(row["c_review_count"]),
        lapse_count=int(row["c_lapse_count"]),
        created_at=from_iso(row["c_created_at"]),
        updated_at=from_iso(row["c_updated_at"]),
    )
