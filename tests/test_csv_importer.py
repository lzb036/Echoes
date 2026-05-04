from echoes.db.connection import connect
from echoes.db.migrations import migrate
from echoes.db.repositories import EchoesStore
from echoes.importers.csv_importer import import_csv
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

    first = import_csv(csv_path, store=store, srs=srs)
    second = import_csv(csv_path, store=store, srs=srs)

    assert first.words_created == 2
    assert first.cards_created == 2
    assert second.words_created == 0
    assert second.cards_created == 0
    assert store.count_words() == 2
    assert store.count_cards() == 2
