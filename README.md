# Echoes

Echoes is a low-profile Windows terminal spaced-repetition app built with Python, Textual, SQLite, and FSRS.

The app stores data locally in one SQLite file and uses a plain terminal interface. Press `Esc` to switch between the review screen and a fake build-log screen.

## Requirements

- Windows
- PowerShell
- Python 3.12 or newer
- uv

Check Python and uv:

```powershell
python --version
uv --version
```

## Quick Start

```powershell
cd D:\Echoes
uv sync
uv run echoes doctor
uv run echoes import .\items.csv
uv run echoes
```

## Create A CSV File

Create `items.csv` in the project directory:

```powershell
@'
term,definition,phonetic,example,tags
opaque,hard to understand,oʊˈpeɪk,The rule is opaque.,work
terse,brief,tɜːrs,Keep the output terse.,work
subtle,delicate or not obvious,sʌtl,There is a subtle difference.,work
'@ | Set-Content -Encoding UTF8 .\items.csv
```

Supported CSV headers:

```csv
term,definition,phonetic,example,note,tags,source
```

Field notes:

- `term`: required.
- `definition`: optional meaning or answer text.
- `phonetic`: optional pronunciation.
- `example`: optional example sentence.
- `note`: optional extra note.
- `tags`: optional tags. Use `;` or `,` to separate multiple tags.
- `source`: optional import source.

## Import Items

```powershell
uv run echoes import .\items.csv
```

Example output:

```text
ok rows=3 items=3 cards=3 skipped=0
```

Import is deduplicated by item and card type. Running the same import again will not create duplicate cards.

## Start The App

```powershell
uv run echoes
```

Default keys:

- `Space`: reveal answer.
- `1`: Again.
- `2`: Hard.
- `3`: Good.
- `4`: Easy.
- `Esc`: switch cover log on/off.
- `q`: quit.

The default interface is intentionally quiet. You will see the current item first, then press `Space` to reveal the answer, then press `1` to `4` to rate it.

## Boss Key

`Esc` toggles the cover screen.

When the cover screen is active, the app shows a scrolling fake build log. Press `Esc` again to restore the exact review state. This does not create review records or reset the current card.

Change the boss key:

```powershell
uv run echoes config set boss_key f12
```

Restore the default:

```powershell
uv run echoes config set boss_key escape
```

Restart the app after changing key settings.

## Help Hints

By default, visible hints are minimal.

Turn hints on:

```powershell
uv run echoes config set show_help true
```

Turn hints off:

```powershell
uv run echoes config set show_help false
```

Restart the app after changing this setting.

## Cover Log Profiles

Available fake log profiles:

- `docker`
- `git`
- `pytest`

Set profile:

```powershell
uv run echoes config set fake_log_profile docker
uv run echoes config set fake_log_profile git
uv run echoes config set fake_log_profile pytest
```

Restart the app after changing this setting.

## Stats

```powershell
uv run echoes stats
```

Example output:

```text
items=3 cards=3 due=3 reviews=0
```

Meaning:

- `items`: imported item count.
- `cards`: review card count.
- `due`: currently due cards.
- `reviews`: saved review records.

## Database

The default database path on Windows is:

```powershell
%LOCALAPPDATA%\Echoes\echoes.db
```

For the current user, it usually looks like:

```powershell
C:\Users\<username>\AppData\Local\Echoes\echoes.db
```

All local data is stored in this one SQLite file:

- items
- cards
- FSRS state
- review history
- settings

If this file is deleted, the stored data in that database is deleted too.

Use another database file:

```powershell
uv run echoes --db .\data\test.db import .\items.csv
uv run echoes --db .\data\test.db
```

You can also set:

```powershell
$env:ECHOES_DB_PATH = "D:\Echoes\data\custom.db"
uv run echoes
```

## Config

Set a config value:

```powershell
uv run echoes config set boss_key escape
```

Read one config value:

```powershell
uv run echoes config get boss_key
```

Read all config values:

```powershell
uv run echoes config get
```

Current useful config keys:

- `boss_key`
- `show_help`
- `fake_log_profile`
- `review_limit`
- `daily_new_limit`

## Doctor

Check the environment and database path:

```powershell
uv run echoes doctor
```

Example output:

```text
ok db=C:\Users\<username>\AppData\Local\Echoes\echoes.db
python=3.12.3
textual=8.2.5
fsrs=unknown
```

## Development Checks

Run tests:

```powershell
uv run pytest
```

Run lint:

```powershell
uv run ruff check .
```

Check formatting:

```powershell
uv run ruff format . --check
```

Format files:

```powershell
uv run ruff format .
```
