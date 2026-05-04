from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from echoes.config import DEFAULT_SETTINGS
from echoes.models import CardRecord, DueCard, Word
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
class ReplaceBatchOutcome:
    words_created: int
    words_updated: int
    words_reactivated: int
    words_archived: int
    cards_created: int
    cards_reset: int


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

    def replace_word_batch(
        self,
        *,
        words: Sequence[WordImportRow],
        card_type: str,
        card_states: Sequence[tuple[str, datetime]],
        now: datetime | None = None,
    ) -> ReplaceBatchOutcome:
        if len(words) != len(card_states):
            raise ValueError("word and card state counts differ")
        if not words:
            raise ValueError("no valid items to import")

        timestamp = now or utc_now()
        timestamp_iso = to_iso(timestamp)
        normalized_terms = [word.term.strip().lower() for word in words]
        placeholders = ", ".join("?" for _ in normalized_terms)

        words_created = 0
        words_updated = 0
        words_reactivated = 0
        cards_created = 0
        cards_reset = 0

        with self.conn:
            archive_cursor = self.conn.execute(
                f"""
                UPDATE words
                SET archived_at = ?, updated_at = ?
                WHERE archived_at IS NULL
                  AND lower(term) NOT IN ({placeholders})
                """,
                (timestamp_iso, timestamp_iso, *normalized_terms),
            )
            words_archived = archive_cursor.rowcount

            for word, (fsrs_state, due_at) in zip(words, card_states, strict=True):
                existing = self.conn.execute(
                    """
                    SELECT id, archived_at
                    FROM words
                    WHERE lower(term) = lower(?)
                    ORDER BY
                        CASE WHEN archived_at IS NULL THEN 0 ELSE 1 END,
                        id ASC
                    LIMIT 1
                    """,
                    (word.term.strip(),),
                ).fetchone()

                if existing is None:
                    word_id = self._insert_word(word, timestamp=timestamp)
                    words_created += 1
                    reset_existing_card = False
                else:
                    word_id = int(existing["id"])
                    reset_existing_card = existing["archived_at"] is not None
                    self._update_imported_word(word_id, word, timestamp=timestamp)
                    words_updated += 1
                    if reset_existing_card:
                        words_reactivated += 1

                existing_card = self.conn.execute(
                    """
                    SELECT id
                    FROM cards
                    WHERE word_id = ? AND card_type = ?
                    LIMIT 1
                    """,
                    (word_id, card_type),
                ).fetchone()

                if existing_card is None:
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
                    cards_created += 1
                elif reset_existing_card:
                    self.conn.execute(
                        """
                        UPDATE cards
                        SET
                            fsrs_state = ?,
                            due_at = ?,
                            last_reviewed_at = NULL,
                            review_count = 0,
                            lapse_count = 0,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            fsrs_state,
                            to_iso(due_at),
                            timestamp_iso,
                            int(existing_card["id"]),
                        ),
                    )
                    cards_reset += 1

        return ReplaceBatchOutcome(
            words_created=words_created,
            words_updated=words_updated,
            words_reactivated=words_reactivated,
            words_archived=words_archived,
            cards_created=cards_created,
            cards_reset=cards_reset,
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

    def _update_imported_word(
        self,
        word_id: int,
        word: WordImportRow,
        *,
        timestamp: datetime,
    ) -> None:
        tags_json = json.dumps(word.tags or [], ensure_ascii=False)
        self.conn.execute(
            """
            UPDATE words
            SET
                term = ?,
                definition = ?,
                phonetic = ?,
                example = ?,
                note = ?,
                tags = ?,
                source = ?,
                archived_at = NULL,
                updated_at = ?
            WHERE id = ?
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
                word_id,
            ),
        )

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
