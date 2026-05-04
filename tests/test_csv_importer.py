from echoes.db.connection import connect
from echoes.db.migrations import migrate
from echoes.db.repositories import EchoesStore
from echoes.importers.csv_importer import ImportMode, import_csv
from echoes.srs.service import SrsService


def make_store(tmp_path) -> EchoesStore:
    conn = connect(tmp_path / "import.db")
    migrate(conn)
    store = EchoesStore(conn)
    store.seed_default_settings()
    return store


def test_csv_import_deduplicates_words_and_cards(tmp_path) -> None:
    csv_path = tmp_path / "items.csv"
    csv_path.write_text(
        "term,definition,example,tags\n"
        "opaque,hard to understand,The rule is opaque.,work;reading\n"
        "terse,brief,Use terse output.,work\n",
        encoding="utf-8",
    )
    store = make_store(tmp_path)
    srs = SrsService()

    first = import_csv(
        csv_path,
        store=store,
        srs=srs,
        mode=ImportMode.MERGE,
    )
    second = import_csv(
        csv_path,
        store=store,
        srs=srs,
        mode=ImportMode.MERGE,
    )

    assert first.words_created == 2
    assert first.cards_created == 2
    assert second.words_created == 0
    assert second.cards_created == 0
    assert store.count_words() == 2
    assert store.count_cards() == 2


def test_csv_import_replaces_active_batch(tmp_path) -> None:
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
    srs = SrsService()

    first = import_csv(first_csv, store=store, srs=srs, batch_size=2)
    second = import_csv(second_csv, store=store, srs=srs, batch_size=2)

    assert first.words_created == 2
    assert first.words_archived == 0
    assert second.words_created == 2
    assert second.words_archived == 2
    assert store.count_words() == 2
    assert store.count_cards() == 2
    assert store.find_word_by_term("opaque") is None
    assert store.find_word_by_term("lucid") is not None


def test_csv_import_replace_requires_expected_batch_size(tmp_path) -> None:
    csv_path = tmp_path / "items.csv"
    csv_path.write_text(
        "term,definition\nopaque,hard to understand\nterse,brief\n",
        encoding="utf-8",
    )
    store = make_store(tmp_path)

    try:
        import_csv(csv_path, store=store, srs=SrsService(), batch_size=60)
    except ValueError as exc:
        assert "expected 60 valid items, found 2" in str(exc)
    else:
        raise AssertionError("expected replace import to enforce batch size")


def test_csv_import_replace_reactivates_and_resets_returning_items(tmp_path) -> None:
    first_csv = tmp_path / "first.csv"
    first_csv.write_text(
        "term,definition\nopaque,old\nterse,brief\n",
        encoding="utf-8",
    )
    second_csv = tmp_path / "second.csv"
    second_csv.write_text(
        "term,definition\nlucid,clear\nspare,plain\n",
        encoding="utf-8",
    )
    third_csv = tmp_path / "third.csv"
    third_csv.write_text(
        "term,definition\nopaque,new\nspare,plain\n",
        encoding="utf-8",
    )
    store = make_store(tmp_path)
    srs = SrsService()

    import_csv(first_csv, store=store, srs=srs, batch_size=2)
    import_csv(second_csv, store=store, srs=srs, batch_size=2)
    result = import_csv(third_csv, store=store, srs=srs, batch_size=2)

    assert result.words_created == 0
    assert result.words_updated == 2
    assert result.words_reactivated == 1
    assert result.cards_reset == 1
    assert result.words_archived == 1
    assert store.count_words() == 2
    assert store.find_word_by_term("opaque").definition == "new"


def test_csv_import_replace_does_not_reset_current_batch_cards(tmp_path) -> None:
    csv_path = tmp_path / "items.csv"
    csv_path.write_text(
        "term,definition\nopaque,old\nterse,brief\n",
        encoding="utf-8",
    )
    updated_csv = tmp_path / "updated.csv"
    updated_csv.write_text(
        "term,definition\nopaque,new\nterse,brief\n",
        encoding="utf-8",
    )
    store = make_store(tmp_path)
    srs = SrsService()

    import_csv(csv_path, store=store, srs=srs, batch_size=2)
    original = store.find_word_by_term("opaque")
    assert original is not None
    original_card = store.find_card(int(original.id), "recognition")
    assert original_card is not None

    result = import_csv(updated_csv, store=store, srs=srs, batch_size=2)
    updated = store.find_word_by_term("opaque")
    assert updated is not None
    updated_card = store.find_card(int(updated.id), "recognition")

    assert result.cards_reset == 0
    assert updated.definition == "new"
    assert updated_card is not None
    assert updated_card.fsrs_state == original_card.fsrs_state
