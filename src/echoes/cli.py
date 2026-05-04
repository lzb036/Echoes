from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fsrs
import textual

from echoes.app import EchoesApp
from echoes.config import build_config, default_db_path
from echoes.db.connection import connect
from echoes.db.migrations import migrate
from echoes.db.repositories import EchoesStore
from echoes.importers.csv_importer import ImportMode, import_csv
from echoes.srs.service import SrsService

DEFAULT_IMPORT_BATCH_SIZE = 60


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    db_path = args.db or default_db_path()
    conn = connect(db_path)
    try:
        migrate(conn)
        store = EchoesStore(conn)
        store.seed_default_settings()

        if args.command == "import":
            mode = ImportMode(args.mode)
            try:
                result = import_csv(
                    args.path,
                    store=store,
                    srs=SrsService(),
                    card_type=args.card_type,
                    mode=mode,
                    batch_size=_resolve_batch_size(args) if mode == ImportMode.REPLACE else None,
                )
            except ValueError as exc:
                print(f"error {exc}")
                raise SystemExit(1) from exc
            print(
                "ok "
                f"rows={result.rows_seen} "
                f"items={result.words_created} "
                f"updated={result.words_updated} "
                f"archived={result.words_archived} "
                f"cards={result.cards_created} "
                f"reset={result.cards_reset} "
                f"skipped={result.skipped}"
            )
            return

        if args.command == "stats":
            print(
                "items="
                f"{store.count_words()} cards={store.count_cards()} "
                f"due={store.count_due_cards()} reviews={store.count_reviews()}"
            )
            return

        if args.command == "doctor":
            _doctor(db_path)
            return

        if args.command == "config":
            _config_command(store, args)
            return

        config = build_config(db_path=db_path, settings=store.get_settings())
        EchoesApp(store=store, srs=SrsService(), config=config).run()
    finally:
        conn.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="echoes")
    parser.add_argument("--db", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command")

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("path", type=Path)
    import_parser.add_argument("--card-type", default="recognition")
    import_parser.add_argument(
        "--mode",
        choices=[mode.value for mode in ImportMode],
        default=ImportMode.REPLACE.value,
    )
    import_parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Expected valid item count for replace imports. Use 0 to disable.",
    )

    subparsers.add_parser("stats")
    subparsers.add_parser("doctor")

    config_parser = subparsers.add_parser("config")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    set_parser = config_subparsers.add_parser("set")
    set_parser.add_argument("key")
    set_parser.add_argument("value")
    get_parser = config_subparsers.add_parser("get")
    get_parser.add_argument("key", nargs="?")
    return parser


def _doctor(db_path: Path) -> None:
    fsrs_version = getattr(fsrs, "__version__", "unknown")
    print(f"ok db={db_path}")
    print(f"python={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"textual={textual.__version__}")
    print(f"fsrs={fsrs_version}")


def _resolve_batch_size(args: argparse.Namespace) -> int | None:
    if args.batch_size is not None:
        return args.batch_size if args.batch_size > 0 else None
    return DEFAULT_IMPORT_BATCH_SIZE


def _config_command(store: EchoesStore, args: argparse.Namespace) -> None:
    if args.config_command == "set":
        store.set_setting(args.key, args.value)
        print("ok")
        return

    settings = store.get_settings()
    if args.key:
        print(settings.get(args.key, ""))
        return
    for key in sorted(settings):
        print(f"{key}={settings[key]}")
