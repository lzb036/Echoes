from datetime import UTC, datetime

from echoes.db.connection import connect
from echoes.db.migrations import migrate
from echoes.db.repositories import EchoesStore
from echoes.models import PASS_TARGET, ReviewRating

NOW = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def make_store(tmp_path) -> EchoesStore:
    conn = connect(tmp_path / "test.db")
    migrate(conn)
    store = EchoesStore(conn)
    store.seed_default_settings()
    return store


def test_store_tracks_three_pass_progress_and_records_reviews(tmp_path) -> None:
    store = make_store(tmp_path)
    word = store.create_word(term="opaque", definition="hard to understand", now=NOW)
    card = store.create_card(word_id=int(word.id), card_type="recognition", now=NOW)

    study_card = store.next_study_card()
    assert study_card is not None
    assert study_card.word.term == "opaque"
    assert study_card.card.pass_count == 0

    store.apply_review(int(card.id), ReviewRating.GOOD, reviewed_at=NOW, elapsed_ms=900)
    updated = store.get_card(int(card.id))
    assert updated is not None
    assert updated.pass_count == 1
    assert updated.completed_at is None

    store.apply_review(int(card.id), ReviewRating.HARD, reviewed_at=NOW, elapsed_ms=900)
    updated = store.get_card(int(card.id))
    assert updated is not None
    assert updated.pass_count == 1

    store.apply_review(int(card.id), ReviewRating.AGAIN, reviewed_at=NOW, elapsed_ms=900)
    updated = store.get_card(int(card.id))
    assert updated is not None
    assert updated.pass_count == 0

    for _ in range(PASS_TARGET):
        store.apply_review(int(card.id), ReviewRating.EASY, reviewed_at=NOW, elapsed_ms=900)

    updated = store.get_card(int(card.id))
    assert updated is not None
    assert updated.pass_count == PASS_TARGET
    assert updated.completed_at == NOW
    assert store.count_reviews() == 6
    assert store.count_remaining_cards() == 0
    assert store.next_study_card() is None

    stats = store.review_stats()
    assert stats.total_cards == 1
    assert stats.completed_cards == 1
    assert stats.remaining_cards == 0


def test_settings_are_seeded_and_updated(tmp_path) -> None:
    store = make_store(tmp_path)

    assert store.get_settings()["boss_key"] == "escape"
    store.set_setting("boss_key", "f12")

    assert store.get_settings()["boss_key"] == "f12"


def test_migration_rebuilds_legacy_fsrs_tables(tmp_path) -> None:
    conn = connect(tmp_path / "legacy.db")
    with conn:
        conn.executescript(
            """
            CREATE TABLE words (
                id INTEGER PRIMARY KEY,
                term TEXT NOT NULL,
                definition TEXT NOT NULL DEFAULT '',
                phonetic TEXT NOT NULL DEFAULT '',
                example TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                source TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT
            );
            CREATE TABLE cards (
                id INTEGER PRIMARY KEY,
                word_id INTEGER NOT NULL,
                card_type TEXT NOT NULL,
                fsrs_state TEXT NOT NULL,
                due_at TEXT NOT NULL,
                last_reviewed_at TEXT,
                review_count INTEGER NOT NULL DEFAULT 0,
                lapse_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE reviews (
                id INTEGER PRIMARY KEY,
                card_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                reviewed_at TEXT NOT NULL,
                elapsed_ms INTEGER,
                scheduled_days REAL,
                state_before TEXT NOT NULL,
                state_after TEXT NOT NULL,
                is_manual INTEGER NOT NULL DEFAULT 0
            );
            INSERT INTO words(term, created_at, updated_at)
            VALUES ('legacy', '2026-01-01', '2026-01-01');
            INSERT INTO cards(word_id, card_type, fsrs_state, due_at, created_at, updated_at)
            VALUES (1, 'recognition', '{}', '2026-01-01', '2026-01-01', '2026-01-01');
            INSERT INTO reviews(card_id, rating, reviewed_at, state_before, state_after)
            VALUES (1, 3, '2026-01-01', '{}', '{}');
            """
        )

    migrate(conn)
    card_columns = {row["name"] for row in conn.execute("PRAGMA table_info(cards)").fetchall()}
    review_columns = {row["name"] for row in conn.execute("PRAGMA table_info(reviews)").fetchall()}

    assert "pass_count" in card_columns
    assert "fsrs_state" not in card_columns
    assert "pass_count_before" in review_columns
    assert "state_before" not in review_columns

    store = EchoesStore(conn)
    word = store.create_word(term="fresh", definition="new", now=NOW)
    card = store.create_card(word_id=int(word.id), card_type="recognition", now=NOW)
    store.apply_review(int(card.id), ReviewRating.GOOD, reviewed_at=NOW, elapsed_ms=100)

    assert store.get_card(int(card.id)).pass_count == 1


def test_next_study_card_prefers_lower_pass_count(tmp_path) -> None:
    store = make_store(tmp_path)
    first_word = store.create_word(term="first", now=NOW)
    second_word = store.create_word(term="second", now=NOW)
    first_card = store.create_card(word_id=int(first_word.id), card_type="recognition", now=NOW)
    store.create_card(word_id=int(second_word.id), card_type="recognition", now=NOW)

    store.apply_review(int(first_card.id), ReviewRating.GOOD, reviewed_at=NOW, elapsed_ms=100)

    next_card = store.next_study_card()
    assert next_card is not None
    assert next_card.word.term == "second"
