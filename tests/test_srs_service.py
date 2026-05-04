from datetime import UTC, datetime

from echoes.models import CardRecord, ReviewRating
from echoes.srs.service import SrsService

NOW = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def test_srs_review_maps_all_ratings_to_distinct_due_times() -> None:
    srs = SrsService(clock=lambda: NOW)
    state, due_at = srs.create_new_card_state()
    card = CardRecord(
        id=1,
        word_id=1,
        card_type="recognition",
        fsrs_state=state,
        due_at=due_at,
        last_reviewed_at=None,
        review_count=0,
        lapse_count=0,
        created_at=NOW,
        updated_at=NOW,
    )

    outcomes = [
        srs.review(card, rating, reviewed_at=NOW, elapsed_ms=1500) for rating in ReviewRating
    ]

    assert len({outcome.due_at for outcome in outcomes}) == 4
    assert all(outcome.reviewed_at.tzinfo is UTC for outcome in outcomes)
    assert outcomes[0].lapse_delta == 1
    assert all(outcome.state_after != state for outcome in outcomes)
