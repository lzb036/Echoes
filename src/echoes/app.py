from __future__ import annotations

from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import RichLog, Static

from echoes.config import AppConfig
from echoes.db.repositories import EchoesStore
from echoes.models import DueCard, ReviewRating
from echoes.srs.service import SrsService
from echoes.time_utils import utc_now
from echoes.ui.fake_logs import FakeLogService
from echoes.ui.keymap import normalize_key

EMPTY_HELP = "Esc Cover  q Quit"
PROMPT_HELP = "Space Answer  Esc Cover  q Quit"
RATING_HELP = "1 Again  2 Hard  3 Good  4 Easy  Esc Cover  q Quit"


class EchoesApp(App[None]):
    TITLE = "build"
    CSS = """
    Screen {
        background: black;
        color: white;
    }

    #study {
        height: 100%;
        padding: 1 2;
    }

    #term {
        height: auto;
        margin-bottom: 1;
        text-style: bold;
    }

    #answer {
        height: 1fr;
    }

    #meta {
        height: auto;
        color: white;
        dock: bottom;
    }

    #cover {
        height: 100%;
        padding: 0 1;
        background: black;
        color: white;
    }
    """
    BINDINGS = [
        Binding("space", "reveal", show=False),
        Binding("1", "rate_again", show=False),
        Binding("2", "rate_hard", show=False),
        Binding("3", "rate_good", show=False),
        Binding("4", "rate_easy", show=False),
        Binding("q", "quit", show=False),
    ]

    def __init__(self, *, store: EchoesStore, srs: SrsService, config: AppConfig) -> None:
        super().__init__()
        self.store = store
        self.srs = srs
        self.config = config
        self.fake_logs = FakeLogService(profile=config.fake_log_profile)
        self.current: DueCard | None = None
        self.answer_revealed = False
        self.started_at: datetime | None = None
        self.cover_active = False

    def compose(self) -> ComposeResult:
        with Container(id="study"):
            yield Static("", id="term", markup=False)
            yield Static("", id="answer", markup=False)
            yield Static("", id="meta", markup=False)
        yield RichLog(
            max_lines=self.fake_logs.max_lines,
            wrap=False,
            highlight=False,
            markup=False,
            auto_scroll=True,
            id="cover",
        )

    def on_mount(self) -> None:
        self.bind(normalize_key(self.config.boss_key), "toggle_cover", show=False)
        self.query_one("#cover", RichLog).display = False
        cover = self.query_one("#cover", RichLog)
        for line in self.fake_logs.seed_lines(28):
            cover.write(line, scroll_end=True)
        self.set_interval(0.35, self._tick_cover)
        self._load_next_card()

    def action_toggle_cover(self) -> None:
        self.cover_active = not self.cover_active
        self.query_one("#study", Container).display = not self.cover_active
        self.query_one("#cover", RichLog).display = self.cover_active
        if self.cover_active:
            self._tick_cover()

    def action_reveal(self) -> None:
        if self.cover_active or self.current is None:
            return
        self.answer_revealed = True
        self._render_study()

    def action_rate_again(self) -> None:
        self._rate(ReviewRating.AGAIN)

    def action_rate_hard(self) -> None:
        self._rate(ReviewRating.HARD)

    def action_rate_good(self) -> None:
        self._rate(ReviewRating.GOOD)

    def action_rate_easy(self) -> None:
        self._rate(ReviewRating.EASY)

    def _rate(self, rating: ReviewRating) -> None:
        if self.cover_active or self.current is None or not self.answer_revealed:
            return
        started = self.started_at or utc_now()
        elapsed_ms = int((utc_now() - started).total_seconds() * 1000)
        outcome = self.srs.review(self.current.card, rating, elapsed_ms=elapsed_ms)
        self.store.apply_review(int(self.current.card.id), outcome)
        self._load_next_card()

    def _load_next_card(self) -> None:
        self.current = self.store.next_due_card()
        self.answer_revealed = False
        self.started_at = utc_now()
        self._render_study()

    def _render_study(self) -> None:
        term = self.query_one("#term", Static)
        answer = self.query_one("#answer", Static)
        meta = self.query_one("#meta", Static)

        if self.current is None:
            term.update("No due items.")
            answer.update("")
            meta.update(EMPTY_HELP)
            return

        word = self.current.word
        term.update(word.term)
        if not self.answer_revealed:
            answer.update("")
            meta.update(PROMPT_HELP)
            return

        details = [
            part for part in [word.definition, _phonetic(word.phonetic), word.example] if part
        ]
        answer.update("\n".join(details) if details else "(empty)")
        meta.update(RATING_HELP)

    def _tick_cover(self) -> None:
        if not self.cover_active:
            return
        cover = self.query_one("#cover", RichLog)
        cover.write(self.fake_logs.next_line(), scroll_end=True)


def _phonetic(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    return f"/{stripped.strip('/')}/"
