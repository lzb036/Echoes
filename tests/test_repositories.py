from datetime import UTC, datetime

from echoes.db.connection import connect
from echoes.db.migrations import migrate
from echoes.db.repositories import EchoesStore
from echoes.models import ReviewRating
from echoes.srs.service import SrsService

NOW = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def make_store(tmp_path) -> EchoesStore:
    conn = connect(tmp_path / "test.db")
    migrate(conn)
    store = EchoesStore(conn)
    store.seed_default_settings()
    return store


def test_store_creates_due_card_and_records_review(tmp_path) -> None:
    store = make_store(tmp_path)
    srs = SrsService(clock=lambda: NOW)
    word = store.create_word(term="opaque", definition="hard to understand", now=NOW)
    state, due_at = srs.create_new_card_state(now=NOW)
    card = store.create_card(
        word_id=int(word.id),
        card_type="recognition",
        fsrs_state=state,
        due_at=due_at,
        now=NOW,
    )

    due = store.next_due_card(now=NOW)
    assert due is not None
    assert due.word.term == "opaque"

    outcome = srs.review(card, ReviewRating.GOOD, reviewed_at=NOW, elapsed_ms=900)
    store.apply_review(int(card.id), outcome)
    updated = store.get_card(int(card.id))

    assert updated is not None
    assert updated.review_count == 1
    assert store.count_reviews() == 1
    assert store.count_due_cards(now=NOW) == 0


def test_settings_are_seeded_and_updated(tmp_path) -> None:
    store = make_store(tmp_path)

    assert store.get_settings()["boss_key"] == "escape"
    store.set_setting("boss_key", "f12")

    assert store.get_settings()["boss_key"] == "f12"
