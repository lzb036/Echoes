from datetime import UTC, datetime

from echoes.db.connection import connect
from echoes.db.migrations import migrate
from echoes.db.repositories import EchoesStore
from echoes.models import PASS_TARGET, ReviewRating
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
    assert updated.pass_count == 1
    assert updated.completed_at is None
    assert store.count_reviews() == 1
    assert store.count_due_cards(now=NOW) == 0

    stats = store.review_stats(now=NOW)
    assert stats.total_cards == 1
    assert stats.completed_cards == 0
    assert stats.remaining_cards == 1


def test_settings_are_seeded_and_updated(tmp_path) -> None:
    store = make_store(tmp_path)

    assert store.get_settings()["boss_key"] == "escape"
    store.set_setting("boss_key", "f12")

    assert store.get_settings()["boss_key"] == "f12"


def test_pass_count_completes_card_after_three_good_reviews(tmp_path) -> None:
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

    current = card
    for _index in range(PASS_TARGET):
        outcome = srs.review(current, ReviewRating.GOOD, reviewed_at=NOW, elapsed_ms=900)
        store.apply_review(int(current.id), outcome)
        current = store.get_card(int(card.id))

    assert current is not None
    assert current.pass_count == PASS_TARGET
    assert current.completed_at is not None
    assert store.next_due_card(now=NOW) is None
    assert store.review_stats(now=NOW).completed_cards == 1


def test_again_resets_pass_count_and_hard_keeps_it(tmp_path) -> None:
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

    good = srs.review(card, ReviewRating.GOOD, reviewed_at=NOW, elapsed_ms=900)
    store.apply_review(int(card.id), good)
    after_good = store.get_card(int(card.id))
    assert after_good.pass_count == 1

    hard = srs.review(after_good, ReviewRating.HARD, reviewed_at=NOW, elapsed_ms=900)
    store.apply_review(int(card.id), hard)
    after_hard = store.get_card(int(card.id))
    assert after_hard.pass_count == 1

    again = srs.review(after_hard, ReviewRating.AGAIN, reviewed_at=NOW, elapsed_ms=900)
    store.apply_review(int(card.id), again)
    after_again = store.get_card(int(card.id))
    assert after_again.pass_count == 0
