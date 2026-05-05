from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from echoes.db.repositories import EchoesStore, WordImportRow

DEFAULT_BATCH_SIZE = 60


@dataclass(frozen=True)
class ImportResult:
    rows_seen: int
    words_created: int
    cards_created: int
    skipped: int
    words_deleted: int
    cards_deleted: int
    reviews_deleted: int


def import_csv(
    path: Path,
    *,
    store: EchoesStore,
    card_type: str = "recognition",
    batch_size: int | None = DEFAULT_BATCH_SIZE,
) -> ImportResult:
    rows_seen, rows, skipped = _read_import_rows(path)
    if batch_size is not None and len(rows) != batch_size:
        raise ValueError(f"expected {batch_size} valid items, found {len(rows)}")

    outcome = store.rebuild_word_batch(
        words=rows,
        card_type=card_type,
    )
    return ImportResult(
        rows_seen=rows_seen,
        words_created=outcome.words_created,
        cards_created=outcome.cards_created,
        skipped=skipped,
        words_deleted=outcome.words_deleted,
        cards_deleted=outcome.cards_deleted,
        reviews_deleted=outcome.reviews_deleted,
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
