from pathlib import Path

from echoes.config import default_data_dir, default_db_path


def test_default_db_path_is_project_local(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ECHOES_HOME", raising=False)
    monkeypatch.delenv("ECHOES_DB_PATH", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-app-data"))

    assert default_data_dir() == tmp_path / "data"
    assert default_db_path() == tmp_path / "data" / "echoes.db"


def test_environment_can_override_default_paths(monkeypatch, tmp_path) -> None:
    home = tmp_path / "portable-data"
    db_path = tmp_path / "custom" / "custom.db"
    monkeypatch.setenv("ECHOES_HOME", str(home))
    monkeypatch.delenv("ECHOES_DB_PATH", raising=False)

    assert default_data_dir() == home
    assert default_db_path() == home / "echoes.db"

    monkeypatch.setenv("ECHOES_DB_PATH", str(db_path))
    assert default_db_path() == Path(db_path)
