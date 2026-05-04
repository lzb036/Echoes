# Echoes

A low-profile Windows terminal spaced-repetition app built with Python, Textual, SQLite, and FSRS.

## Quick Start

```powershell
uv sync
uv run echoes doctor
uv run echoes import .\items.csv
uv run echoes
```

CSV import accepts these headers:

```csv
term,definition,phonetic,example,note,tags,source
```

Inside the app:

- `Space`: reveal answer
- `1`: Again
- `2`: Hard
- `3`: Good
- `4`: Easy
- `Esc`: switch cover log on/off
- `q`: quit

The default database path is `%LOCALAPPDATA%\Echoes\echoes.db` on Windows. Set `ECHOES_DB_PATH` to override it.
