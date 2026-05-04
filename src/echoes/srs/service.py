from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from fsrs import Rating, Scheduler

from echoes.models import CardRecord, ReviewRating
from echoes.srs.serializers import card_from_json, card_to_json, new_card_json
from echoes.time_utils import ensure_utc, utc_now


@dataclass(frozen=True)
class ReviewOutcome:
    rating: ReviewRating
    reviewed_at: datetime
    due_at: datetime
    elapsed_ms: int | None
    scheduled_days: float | None
    state_before: str
    state_after: str
    lapse_delta: int


class SrsService:
    def __init__(
        self,
        *,
        scheduler: Scheduler | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.scheduler = scheduler or Scheduler(enable_fuzzing=False)
        self.clock = clock or utc_now

    def create_new_card_state(self, *, now: datetime | None = None) -> tuple[str, datetime]:
        return new_card_json(now=now or self.clock())

    def review(
        self,
        card_record: CardRecord,
        rating: ReviewRating,
        *,
        reviewed_at: datetime | None = None,
        elapsed_ms: int | None = None,
    ) -> ReviewOutcome:
        review_time = ensure_utc(reviewed_at or self.clock())
        source_card = card_from_json(card_record.fsrs_state)
        reviewed_card, _log = self.scheduler.review_card(
            source_card,
            Rating(int(rating)),
            review_time,
            elapsed_ms,
        )
        due_at = ensure_utc(reviewed_card.due)
        scheduled_days = (due_at - review_time).total_seconds() / 86400
        state_after = card_to_json(reviewed_card)
        return ReviewOutcome(
            rating=rating,
            reviewed_at=review_time,
            due_at=due_at,
            elapsed_ms=elapsed_ms,
            scheduled_days=scheduled_days,
            state_before=card_record.fsrs_state,
            state_after=state_after,
            lapse_delta=1 if rating == ReviewRating.AGAIN else 0,
        )
