from __future__ import annotations

from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import RichLog, Static

from echoes.config import AppConfig
from echoes.db.repositories import EchoesStore
from echoes.models import PASS_TARGET, ReviewRating, ReviewStats, StudyCard, Word
from echoes.time_utils import utc_now
from echoes.ui.fake_logs import FakeLogService
from echoes.ui.keymap import normalize_key

EMPTY_HELP = "Esc Cover  q Quit"
PROMPT_HELP = "e Ex  Space Answer  Esc Cover  q Quit"
RATING_HELP = "1 Again  2 Hard  3 Easy  Esc Cover  q Quit"
ANSWER_HELP = "e Ex  1 Again  2 Hard  3 Easy  Esc Cover  q Quit"


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

    #top {
        height: auto;
        margin-bottom: 1;
    }

    #term {
        width: 1fr;
        height: auto;
        text-style: bold;
    }

    #status {
        width: 22;
        height: auto;
        text-align: right;
    }

    #answer {
        height: 1fr;
    }

    #keys {
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
        Binding("3", "rate_easy", show=False),
        Binding("4", "rate_easy", show=False),
        Binding("e", "example", show=False),
        Binding("q", "quit", show=False),
    ]

    def __init__(self, *, store: EchoesStore, config: AppConfig) -> None:
        super().__init__()
        self.store = store
        self.config = config
        self.fake_logs = FakeLogService(profile=config.fake_log_profile)
        self.current: StudyCard | None = None
        self.stats = ReviewStats(total_cards=0, completed_cards=0)
        self.answer_revealed = False
        self.example_stage = 0
        self.started_at: datetime | None = None
        self.cover_active = False

    def compose(self) -> ComposeResult:
        with Container(id="study"):
            with Horizontal(id="top"):
                yield Static("", id="term", markup=False)
                yield Static("", id="status", markup=False)
            yield Static("", id="answer", markup=False)
            yield Static("", id="keys", markup=False)
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

    def action_rate_easy(self) -> None:
        self._rate(ReviewRating.EASY)

    def action_example(self) -> None:
        if self.cover_active or self.current is None:
            return
        word = self.current.word
        if self.example_stage == 0 and word.example.strip():
            self.example_stage = 1
        elif self.example_stage < 2 and word.note.strip():
            self.example_stage = 2
        self._render_study()

    def _rate(self, rating: ReviewRating) -> None:
        if self.cover_active or self.current is None or not self.answer_revealed:
            return
        now = utc_now()
        started = self.started_at or now
        elapsed_ms = int((now - started).total_seconds() * 1000)
        self.store.apply_review(
            int(self.current.card.id),
            rating,
            reviewed_at=now,
            elapsed_ms=elapsed_ms,
        )
        self._load_next_card()

    def _load_next_card(self) -> None:
        now = utc_now()
        self.current = self.store.next_study_card()
        self.stats = self.store.review_stats()
        self.answer_revealed = False
        self.example_stage = 0
        self.started_at = now
        self._render_study()

    def _render_study(self) -> None:
        term = self.query_one("#term", Static)
        status = self.query_one("#status", Static)
        answer = self.query_one("#answer", Static)
        keys = self.query_one("#keys", Static)

        if self.current is None:
            term.update("No items.")
            status.update(_status_text(None, self.stats))
            answer.update("")
            keys.update(EMPTY_HELP)
            return

        word = self.current.word
        term.update(_term_text(word))
        status.update(_status_text(self.current, self.stats))
        if not self.answer_revealed:
            answer.update(_prompt_text(word, example_stage=self.example_stage))
            keys.update(PROMPT_HELP)
            return

        answer.update(_answer_text(word, example_stage=self.example_stage))
        keys.update(ANSWER_HELP)

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


def _term_text(word: Word) -> str:
    phonetic = _phonetic(word.phonetic)
    if not phonetic:
        return word.term
    return f"{word.term}  {phonetic}"


def _answer_text(word: Word, *, example_stage: int) -> str:
    details = [word.definition] if word.definition else []
    example_lines = _example_lines(word, example_stage=example_stage)
    if details and example_lines:
        details.append("")
    details.extend(example_lines)
    return "\n".join(details) if details else "(empty)"


def _prompt_text(word: Word, *, example_stage: int) -> str:
    return "\n".join(_example_lines(word, example_stage=example_stage))


def _example_lines(word: Word, *, example_stage: int) -> list[str]:
    details: list[str] = []
    if example_stage >= 1 and word.example.strip():
        details.append(word.example)
    if example_stage >= 2 and word.note.strip():
        details.append(word.note)
    return details


def _status_text(current: StudyCard | None, stats: ReviewStats) -> str:
    pass_count = _current_pass_count(current)
    return (
        f"{_progress_bar(stats.completed_cards, stats.total_cards, width=12)} "
        f"{stats.completed_cards}/{stats.total_cards}\n"
        f"{_progress_bar(pass_count, PASS_TARGET, width=PASS_TARGET)} {pass_count}/{PASS_TARGET}"
    )


def _current_pass_count(current: StudyCard | None) -> int:
    if current is not None:
        return min(PASS_TARGET, max(0, current.card.pass_count))
    return PASS_TARGET


def _progress_bar(value: int, total: int, *, width: int) -> str:
    filled = 0 if total <= 0 else min(width, max(0, round((value / total) * width)))
    return f"[{'#' * filled}{'-' * (width - filled)}]"
