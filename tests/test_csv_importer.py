from datetime import UTC, datetime

from echoes.db.connection import connect
from echoes.db.migrations import migrate
from echoes.db.repositories import EchoesStore
from echoes.importers.csv_importer import import_csv
from echoes.models import ReviewRating
from echoes.srs.service import SrsService

NOW = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def make_store(tmp_path) -> EchoesStore:
    conn = connect(tmp_path / "import.db")
    migrate(conn)
    store = EchoesStore(conn)
    store.seed_default_settings()
    return store


def test_csv_import_rebuilds_the_database_batch(tmp_path) -> None:
    first_csv = tmp_path / "first.csv"
    first_csv.write_text(
        "term,definition,example,tags\n"
        "opaque,hard to understand,The rule is opaque.,day1\n"
        "terse,brief,Use terse output.,day1\n",
        encoding="utf-8",
    )
    second_csv = tmp_path / "second.csv"
    second_csv.write_text(
        "term,definition,example,tags\n"
        "lucid,clear,The note is lucid.,day2\n"
        "spare,plain,Keep the UI spare.,day2\n",
        encoding="utf-8",
    )
    store = make_store(tmp_path)
    srs = SrsService(clock=lambda: NOW)

    import_csv(first_csv, store=store, srs=srs, batch_size=2)
    card = store.next_due_card(now=NOW)
    assert card is not None
    outcome = srs.review(card.card, ReviewRating.GOOD, reviewed_at=NOW, elapsed_ms=500)
    store.apply_review(int(card.card.id), outcome)
    assert store.count_reviews() == 1

    result = import_csv(second_csv, store=store, srs=srs, batch_size=2)

    assert result.words_created == 2
    assert result.cards_created == 2
    assert result.words_deleted == 2
    assert result.cards_deleted == 2
    assert result.reviews_deleted == 1
    assert store.count_words() == 2
    assert store.count_cards() == 2
    assert store.count_reviews() == 0
    assert store.find_word_by_term("opaque") is None
    assert store.find_word_by_term("lucid") is not None


def test_csv_import_requires_expected_batch_size_before_deleting_old_data(tmp_path) -> None:
    first_csv = tmp_path / "first.csv"
    first_csv.write_text(
        "term,definition\nopaque,hard to understand\nterse,brief\n",
        encoding="utf-8",
    )
    short_csv = tmp_path / "short.csv"
    short_csv.write_text(
        "term,definition\nlucid,clear\n",
        encoding="utf-8",
    )
    store = make_store(tmp_path)
    srs = SrsService()
    import_csv(first_csv, store=store, srs=srs, batch_size=2)

    try:
        import_csv(short_csv, store=store, srs=srs, batch_size=2)
    except ValueError as exc:
        assert "expected 2 valid items, found 1" in str(exc)
    else:
        raise AssertionError("expected import to enforce batch size")

    assert store.count_words() == 2
    assert store.count_cards() == 2
    assert store.find_word_by_term("opaque") is not None


def test_csv_import_skips_blank_and_duplicate_terms(tmp_path) -> None:
    csv_path = tmp_path / "items.csv"
    csv_path.write_text(
        "term,definition\n"
        "opaque,hard to understand\n"
        "Opaque,duplicate\n"
        ",missing term\n"
        "terse,brief\n",
        encoding="utf-8",
    )
    store = make_store(tmp_path)

    result = import_csv(csv_path, store=store, srs=SrsService(), batch_size=2)

    assert result.rows_seen == 4
    assert result.skipped == 2
    assert result.words_created == 2
    assert store.count_words() == 2
    assert store.find_word_by_term("opaque").definition == "hard to understand"
