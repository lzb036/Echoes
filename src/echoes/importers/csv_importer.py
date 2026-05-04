from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from echoes.db.repositories import EchoesStore
from echoes.srs.service import SrsService


@dataclass(frozen=True)
class ImportResult:
    rows_seen: int
    words_created: int
    cards_created: int
    skipped: int


def import_csv(
    path: Path,
    *,
    store: EchoesStore,
    srs: SrsService,
    card_type: str = "recognition",
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
