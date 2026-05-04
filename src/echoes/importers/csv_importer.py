from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from echoes.db.repositories import EchoesStore, WordImportRow
from echoes.srs.service import SrsService

DEFAULT_BATCH_SIZE = 60


class ImportMode(StrEnum):
    REPLACE = "replace"
    MERGE = "merge"


@dataclass(frozen=True)
class ImportResult:
    rows_seen: int
    words_created: int
    cards_created: int
    skipped: int
    words_updated: int = 0
    words_reactivated: int = 0
    words_archived: int = 0
    cards_reset: int = 0


def import_csv(
    path: Path,
    *,
    store: EchoesStore,
    srs: SrsService,
    card_type: str = "recognition",
    mode: ImportMode = ImportMode.REPLACE,
    batch_size: int | None = DEFAULT_BATCH_SIZE,
) -> ImportResult:
    if mode == ImportMode.REPLACE:
        return _replace_csv(
            path,
            store=store,
            srs=srs,
            card_type=card_type,
            batch_size=batch_size,
        )
    return _merge_csv(path, store=store, srs=srs, card_type=card_type)


def _merge_csv(
    path: Path,
    *,
    store: EchoesStore,
    srs: SrsService,
    card_type: str,
) -> ImportResult:
    rows_seen = 0
    words_created = 0
    cards_created = 0
    skipped = 0

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rows_seen += 1
            term = (row.get("term") or "").strip()
            if not term:
                skipped += 1
                continue

            word, created_word = store.ensure_word(
                term=term,
                definition=row.get("definition") or "",
                phonetic=row.get("phonetic") or "",
                example=row.get("example") or "",
                note=row.get("note") or "",
                tags=_parse_tags(row.get("tags") or ""),
                source=row.get("source") or path.name,
            )
            words_created += 1 if created_word else 0

            fsrs_state, due_at = srs.create_new_card_state()
            _card, created_card = store.ensure_card(
                word_id=int(word.id),
                card_type=card_type,
                fsrs_state=fsrs_state,
                due_at=due_at,
            )
            cards_created += 1 if created_card else 0

    return ImportResult(
        rows_seen=rows_seen,
        words_created=words_created,
        cards_created=cards_created,
        skipped=skipped,
    )


def _replace_csv(
    path: Path,
    *,
    store: EchoesStore,
    srs: SrsService,
    card_type: str,
    batch_size: int | None,
) -> ImportResult:
    rows_seen, rows, skipped = _read_import_rows(path)
    if batch_size is not None and len(rows) != batch_size:
        raise ValueError(f"expected {batch_size} valid items, found {len(rows)}")

    card_states = [srs.create_new_card_state() for _row in rows]
    outcome = store.replace_word_batch(
        words=rows,
        card_type=card_type,
        card_states=card_states,
    )
    return ImportResult(
        rows_seen=rows_seen,
        words_created=outcome.words_created,
        words_updated=outcome.words_updated,
        words_reactivated=outcome.words_reactivated,
        words_archived=outcome.words_archived,
        cards_created=outcome.cards_created,
        cards_reset=outcome.cards_reset,
        skipped=skipped,
    )


def _read_import_rows(path: Path) -> tuple[int, list[WordImportRow], int]:
    rows_seen = 0
    skipped = 0
    rows: list[WordImportRow] = []
    seen_terms: set[str] = set()

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            rows_seen += 1
            term = (row.get("term") or "").strip()
            normalized = term.lower()
            if not term or normalized in seen_terms:
                skipped += 1
                continue
            seen_terms.add(normalized)
            rows.append(
                WordImportRow(
                    term=term,
                    definition=row.get("definition") or "",
                    phonetic=row.get("phonetic") or "",
                    example=row.get("example") or "",
                    note=row.get("note") or "",
                    tags=_parse_tags(row.get("tags") or ""),
                    source=row.get("source") or path.name,
                )
            )

    return rows_seen, rows, skipped


def _parse_tags(raw: str) -> list[str]:
    value = raw.strip()
    if not value:
        return []
    if value.startswith("["):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        return []
    separator = ";" if ";" in value else ","
    return [item.strip() for item in value.split(separator) if item.strip()]
