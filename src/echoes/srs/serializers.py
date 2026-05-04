from __future__ import annotations

from datetime import datetime

from fsrs import Card

from echoes.time_utils import ensure_utc, utc_now


def new_card_json(*, now: datetime | None = None) -> tuple[str, datetime]:
    due = ensure_utc(now or utc_now())
    card = Card(due=due)
    return card.to_json(), due


def card_from_json(source: str) -> Card:
    card = Card.from_json(source)
    if card.due is not None:
        card.due = ensure_utc(card.due)
    if card.last_review is not None:
        card.last_review = ensure_utc(card.last_review)
    return card


def card_to_json(card: Card) -> str:
    if card.due is not None:
        card.due = ensure_utc(card.due)
    if card.last_review is not None:
        card.last_review = ensure_utc(card.last_review)
    return card.to_json()
