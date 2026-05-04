import pytest

from echoes.ui.keymap import normalize_key


def test_normalize_key_aliases() -> None:
    assert normalize_key(" Esc ") == "escape"
    assert normalize_key("spacebar") == "space"


def test_normalize_key_rejects_empty() -> None:
    with pytest.raises(ValueError):
        normalize_key(" ")
