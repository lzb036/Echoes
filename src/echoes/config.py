from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SETTINGS: dict[str, str] = {
    "boss_key": "escape",
    "theme": "plain",
    "show_help": "false",
    "show_chinese": "true",
    "fake_log_profile": "docker",
    "daily_new_limit": "60",
    "review_limit": "100",
}


@dataclass(frozen=True)
class AppConfig:
    db_path: Path
    boss_key: str = DEFAULT_SETTINGS["boss_key"]
    fake_log_profile: str = DEFAULT_SETTINGS["fake_log_profile"]
    show_help: bool = False
    review_limit: int = 100


def default_data_dir() -> Path:
    explicit_home = os.environ.get("ECHOES_HOME")
    if explicit_home:
        return Path(explicit_home)

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Echoes"

    return Path.cwd() / "data"


def default_db_path() -> Path:
    explicit_db = os.environ.get("ECHOES_DB_PATH")
    if explicit_db:
        return Path(explicit_db)
    return default_data_dir() / "echoes.db"


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_config(
    *,
    db_path: Path | None = None,
    settings: dict[str, str] | None = None,
) -> AppConfig:
    merged = {**DEFAULT_SETTINGS, **(settings or {})}
    return AppConfig(
        db_path=db_path or default_db_path(),
        boss_key=merged["boss_key"],
        fake_log_profile=merged["fake_log_profile"],
        show_help=parse_bool(merged.get("show_help")),
        review_limit=int(merged["review_limit"]),
    )
