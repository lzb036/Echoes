from __future__ import annotations

ALIASES = {
    "esc": "escape",
    "return": "enter",
    "spacebar": "space",
}


def normalize_key(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("key cannot be empty")
    return ALIASES.get(normalized, normalized)
