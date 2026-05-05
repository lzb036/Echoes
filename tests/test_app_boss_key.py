import asyncio
from datetime import UTC, datetime

from echoes.app import EchoesApp
from echoes.config import build_config
from echoes.db.connection import connect
from echoes.db.migrations import migrate
from echoes.db.repositories import EchoesStore
from echoes.srs.service import SrsService

NOW = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def make_app(tmp_path) -> tuple[EchoesApp, EchoesStore]:
    conn = connect(tmp_path / "app.db")
    migrate(conn)
    store = EchoesStore(conn)
    store.seed_default_settings()
    srs = SrsService(clock=lambda: NOW)
    word = store.create_word(term="opaque", definition="hard to understand", now=NOW)
    state, due_at = srs.create_new_card_state(now=NOW)
    store.create_card(
        word_id=int(word.id),
        card_type="recognition",
        fsrs_state=state,
        due_at=due_at,
        now=NOW,
    )
    config = build_config(db_path=tmp_path / "app.db", settings=store.get_settings())
    return EchoesApp(store=store, srs=srs, config=config), store


def test_boss_key_preserves_current_card_and_writes_no_review(tmp_path) -> None:
    app, store = make_app(tmp_path)

    async def scenario() -> None:
        async with app.run_test() as pilot:
            assert app.current is not None
            card_id = app.current.card.id
            await pilot.press("escape")
            assert app.cover_active is True
            await pilot.press("escape")
            assert app.cover_active is False
            assert app.current is not None
            assert app.current.card.id == card_id

    asyncio.run(scenario())
    assert store.count_reviews() == 0


def test_rating_before_reveal_is_ignored(tmp_path) -> None:
    app, store = make_app(tmp_path)

    async def scenario() -> None:
        async with app.run_test() as pilot:
            await pilot.press("1")

    asyncio.run(scenario())
    assert store.count_reviews() == 0


def test_footer_shows_key_hints_before_and_after_reveal(tmp_path) -> None:
    app, _store = make_app(tmp_path)

    async def scenario() -> None:
        async with app.run_test() as pilot:
            keys = app.query_one("#keys")
            assert str(keys.render()) == "Space Answer  Esc Cover  q Quit"
            await pilot.press("space")
            assert str(keys.render()) == "1 Again  2 Hard  3 Good  4 Easy  Esc Cover  q Quit"

    asyncio.run(scenario())


def test_study_screen_shows_batch_and_card_status(tmp_path) -> None:
    app, _store = make_app(tmp_path)

    async def scenario() -> None:
        async with app.run_test():
            status = app.query_one("#status")
            rendered = str(status.render())
            assert "Batch total=1 reviewed=0 new=1 due=1" in rendered
            assert "Card reviews=0 lapses=0 due=now" in rendered

    asyncio.run(scenario())
