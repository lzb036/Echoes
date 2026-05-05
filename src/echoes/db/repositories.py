from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from echoes.config import DEFAULT_SETTINGS
from echoes.models import (
    AGAIN_DELAY,
    EASY_DELAY,
    GOOD_DELAY,
    HARD_DELAY,
    PASS_TARGET,
    CardRecord,
    ReviewRating,
    ReviewStats,
    StudyCard,
    Word,
)
from echoes.time_utils import from_iso, to_iso, utc_now

REVIEW_TURN_SETTING = "review_turn"


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
                    json.dumps(tags or [], ensure_ascii=False),
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
        now: datetime | None = None,
    ) -> RebuildBatchOutcome:
        if not words:
            raise ValueError("no valid items to import")

        timestamp = now or utc_now()
        timestamp_iso = to_iso(timestamp)
        with self.conn:
            reviews_deleted = self.conn.execute("DELETE FROM reviews").rowcount
            cards_deleted = self.conn.execute("DELETE FROM cards").rowcount
            words_deleted = self.conn.execute("DELETE FROM words").rowcount
            self._set_review_turn(0, timestamp=timestamp)

            for word in words:
                word_id = self._insert_word(word, timestamp=timestamp)
                self.conn.execute(
                    """
                    INSERT INTO cards(
                        word_id, card_type, pass_count, next_review_turn,
                        completed_at, created_at, updated_at
                    )
                    VALUES (?, ?, 0, 0, NULL, ?, ?)
                    """,
                    (word_id, card_type, timestamp_iso, timestamp_iso),
                )

        return RebuildBatchOutcome(
            words_created=len(words),
            cards_created=len(words),
            reviews_deleted=reviews_deleted,
            cards_deleted=cards_deleted,
            words_deleted=words_deleted,
        )

    def _insert_word(self, word: WordImportRow, *, timestamp: datetime) -> int:
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
                json.dumps(word.tags or [], ensure_ascii=False),
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
        now: datetime | None = None,
    ) -> CardRecord:
        timestamp = now or utc_now()
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO cards(
                    word_id, card_type, pass_count, next_review_turn,
                    completed_at, created_at, updated_at
                )
                VALUES (?, ?, 0, 0, NULL, ?, ?)
                """,
                (word_id, card_type, to_iso(timestamp), to_iso(timestamp)),
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
    ) -> tuple[CardRecord, bool]:
        existing = self.find_card(word_id, card_type)
        if existing:
            return existing, False
        return self.create_card(word_id=word_id, card_type=card_type), True

    def get_card(self, card_id: int) -> CardRecord | None:
        row = self.conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        return _card_from_row(row) if row else None

    def next_study_card(self) -> StudyCard | None:
        review_turn = self.review_turn()
        row = self.conn.execute(
            """
            SELECT
                c.id AS c_id,
                c.word_id AS c_word_id,
                c.card_type AS c_card_type,
                c.pass_count AS c_pass_count,
                c.next_review_turn AS c_next_review_turn,
                c.completed_at AS c_completed_at,
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
            WHERE c.completed_at IS NULL AND w.archived_at IS NULL
            ORDER BY
                CASE WHEN c.next_review_turn <= ? THEN 0 ELSE 1 END ASC,
                CASE WHEN c.next_review_turn <= ? THEN c.pass_count ELSE c.next_review_turn END ASC,
                c.next_review_turn ASC,
                c.pass_count ASC,
                c.id ASC
            LIMIT 1
            """,
            (review_turn, review_turn),
        ).fetchone()
        if row is None:
            return None
        return StudyCard(card=_card_from_prefixed_row(row), word=_word_from_prefixed_row(row))

    def apply_review(
        self,
        card_id: int,
        rating: ReviewRating,
        *,
        reviewed_at: datetime | None = None,
        elapsed_ms: int | None = None,
        is_manual: bool = False,
    ) -> None:
        review_time = reviewed_at or utc_now()
        with self.conn:
            row = self.conn.execute(
                "SELECT pass_count, completed_at FROM cards WHERE id = ?",
                (card_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"card not found: {card_id}")

            review_turn = self.review_turn() + 1
            before = int(row["pass_count"])
            after = _next_pass_count(before, rating)
            completed_at = to_iso(review_time) if after >= PASS_TARGET else None
            next_review_turn = review_turn
            review_log_next_turn: int | None = None
            if completed_at is None:
                next_review_turn = review_turn + _review_delay(rating)
                review_log_next_turn = next_review_turn
            self.conn.execute(
                """
                UPDATE cards
                SET pass_count = ?, next_review_turn = ?, completed_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (after, next_review_turn, completed_at, to_iso(utc_now()), card_id),
            )
            self.conn.execute(
                """
                INSERT INTO reviews(
                    card_id, rating, reviewed_at, elapsed_ms,
                    pass_count_before, pass_count_after,
                    review_turn, next_review_turn, is_manual
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card_id,
                    int(rating),
                    to_iso(review_time),
                    elapsed_ms,
                    before,
                    after,
                    review_turn,
                    review_log_next_turn,
                    1 if is_manual else 0,
                ),
            )
            self._set_review_turn(review_turn, timestamp=review_time)

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

    def count_remaining_cards(self) -> int:
        return int(
            self.conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM cards c
                JOIN words w ON w.id = c.word_id
                WHERE c.completed_at IS NULL AND w.archived_at IS NULL
                """
            ).fetchone()["count"]
        )

    def count_reviews(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) AS count FROM reviews").fetchone()["count"])

    def review_stats(self) -> ReviewStats:
        row = self.conn.execute(
            """
            SELECT
                COUNT(*) AS total_cards,
                SUM(CASE WHEN c.completed_at IS NOT NULL THEN 1 ELSE 0 END) AS completed_cards
            FROM cards c
            JOIN words w ON w.id = c.word_id
            WHERE w.archived_at IS NULL
            """
        ).fetchone()
        return ReviewStats(
            total_cards=int(row["total_cards"] or 0),
            completed_cards=int(row["completed_cards"] or 0),
        )

    def review_turn(self) -> int:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (REVIEW_TURN_SETTING,),
        ).fetchone()
        if row is None:
            return 0
        try:
            return max(0, int(row["value"]))
        except ValueError:
            return 0

    def _set_review_turn(self, value: int, *, timestamp: datetime) -> None:
        self.conn.execute(
            """
            INSERT INTO settings(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (REVIEW_TURN_SETTING, str(value), to_iso(timestamp)),
        )


def _next_pass_count(current: int, rating: ReviewRating) -> int:
    if rating == ReviewRating.AGAIN:
        return 0
    if rating in (ReviewRating.GOOD, ReviewRating.EASY):
        return min(PASS_TARGET, current + 1)
    return min(PASS_TARGET, current)


def _review_delay(rating: ReviewRating) -> int:
    if rating == ReviewRating.AGAIN:
        return AGAIN_DELAY
    if rating == ReviewRating.HARD:
        return HARD_DELAY
    if rating == ReviewRating.EASY:
        return EASY_DELAY
    return GOOD_DELAY


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
        pass_count=int(row["pass_count"]),
        next_review_turn=int(row["next_review_turn"]),
        completed_at=from_iso(row["completed_at"]) if row["completed_at"] else None,
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
        pass_count=int(row["c_pass_count"]),
        next_review_turn=int(row["c_next_review_turn"]),
        completed_at=from_iso(row["c_completed_at"]) if row["c_completed_at"] else None,
        created_at=from_iso(row["c_created_at"]),
        updated_at=from_iso(row["c_updated_at"]),
    )
