from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum


class ReviewRating(IntEnum):
    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


@dataclass(frozen=True)
class Word:
    id: int | None
    term: str
    definition: str = ""
    phonetic: str = ""
    example: str = ""
    note: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None


@dataclass(frozen=True)
class CardRecord:
    id: int | None
    word_id: int
    card_type: str
    fsrs_state: str
    due_at: datetime
    last_reviewed_at: datetime | None
    review_count: int
    lapse_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class DueCard:
    card: CardRecord
    word: Word


@dataclass(frozen=True)
class ReviewStats:
    total_cards: int
    reviewed_cards: int
    due_cards: int

    @property
    def new_cards(self) -> int:
        return max(0, self.total_cards - self.reviewed_cards)


@dataclass(frozen=True)
class ReviewRecord:
    id: int | None
    card_id: int
    rating: int
    reviewed_at: datetime
    elapsed_ms: int | None
    scheduled_days: float | None
    state_before: str
    state_after: str
    is_manual: bool = False
