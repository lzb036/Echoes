from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum

PASS_TARGET = 3
AGAIN_DELAY = 2
HARD_DELAY = 4
GOOD_DELAY = 10
EASY_DELAY = 16


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
    pass_count: int
    next_review_turn: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class StudyCard:
    card: CardRecord
    word: Word


@dataclass(frozen=True)
class ReviewStats:
    total_cards: int
    completed_cards: int

    @property
    def remaining_cards(self) -> int:
        return max(0, self.total_cards - self.completed_cards)


@dataclass(frozen=True)
class ReviewRecord:
    id: int | None
    card_id: int
    rating: int
    reviewed_at: datetime
    elapsed_ms: int | None
    pass_count_before: int
    pass_count_after: int
    review_turn: int
    next_review_turn: int | None
    is_manual: bool = False
