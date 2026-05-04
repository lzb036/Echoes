from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field


@dataclass
class FakeLogService:
    profile: str = "docker"
    max_lines: int = 500
    seed: int | None = None
    _counter: int = 0
    _rng: random.Random = field(init=False)
    _lines: deque[str] = field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._lines = deque(maxlen=self.max_lines)

    @property
    def lines(self) -> list[str]:
        return list(self._lines)

    def next_line(self) -> str:
        self._counter += 1
        if self.profile == "git":
            line = self._git_line()
        elif self.profile == "pytest":
            line = self._pytest_line()
        else:
            line = self._docker_line()
        self._lines.append(line)
        return line

    def seed_lines(self, count: int = 24) -> list[str]:
        return [self.next_line() for _ in range(count)]

    def _docker_line(self) -> str:
        step = (self._counter % 14) + 1
        digest = self._rng.randrange(100000, 999999)
        size = self._rng.randrange(128, 8192)
        templates = [
            "#1 [internal] load build definition from Dockerfile",
            "#1 transferring dockerfile: {size}B done",
            "#2 [internal] load metadata for docker.io/library/python:3.12-slim",
            "#3 [auth] registry-1.docker.io request accepted",
            "#4 [base 1/5] FROM docker.io/library/python:3.12-slim@sha256:{digest}",
            "#5 [base 2/5] WORKDIR C:\\work\\services\\api",
            "#6 [base 3/5] COPY pyproject.toml uv.lock ./",
            "#7 [base 4/5] RUN uv sync --frozen --no-dev",
            "#8 [stage 1/3] COPY src ./src",
            "#9 exporting to image",
            "#9 exporting layers {size}.0kB done",
            "#9 writing image sha256:{digest} done",
            "warning: cache metadata not found for layer {step}",
            "=> naming to docker.io/library/service-api:local",
        ]
        return templates[self._counter % len(templates)].format(
            step=step,
            digest=f"{digest:x}",
            size=size,
        )

    def _git_line(self) -> str:
        digest = self._rng.randrange(0x1000000, 0xFFFFFFF)
        files = self._rng.randrange(1, 12)
        templates = [
            "From https://example.invalid/backend/service-api",
            " * branch            main       -> FETCH_HEAD",
            "Updating {old}..{new}",
            "Fast-forward",
            " src/service/module_{files}.py | {files} ++++---",
            " tests/test_module_{files}.py  | {files} +++++",
            " {files} files changed, {added} insertions(+), {removed} deletions(-)",
            "commit {new}",
            "Author: build <build@example.invalid>",
            "Date:   Mon May 04 13:22:10 2026 +0000",
        ]
        return templates[self._counter % len(templates)].format(
            old=f"{digest - 1000:x}",
            new=f"{digest:x}",
            files=files,
            added=files * 7,
            removed=files * 2,
        )

    def _pytest_line(self) -> str:
        module = self._rng.choice(["api", "jobs", "storage", "auth", "config"])
        index = self._rng.randrange(1, 80)
        templates = [
            "============================= test session starts =============================",
            "platform win32 -- Python 3.12.3, pytest-9.0.3",
            "rootdir: D:\\repo\\backend",
            "collected {index} items",
            "tests\\test_{module}.py .",
            "tests\\test_{module}.py ..",
            "tests\\test_{module}.py ....",
            "coverage: module {module} branch check complete",
            "============================== "
            "{index} passed in 4.{tail}s "
            "==============================",
        ]
        return templates[self._counter % len(templates)].format(
            module=module,
            index=index,
            tail=self._rng.randrange(10, 99),
        )
