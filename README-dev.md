# Echoes Development

This document is for development and release work. For normal use, see `README.md`.

## Requirements

- Windows
- PowerShell
- Python 3.12 or newer
- uv

Check tools:

```powershell
python --version
uv --version
```

## Setup

```powershell
cd D:\Echoes
uv sync
uv run echoes doctor
```

## Run Locally

Prepare an `items.csv` with exactly 60 valid items, then run:

```powershell
uv run echoes import .\items.csv
uv run echoes
```

Local development defaults to:

```text
data\echoes.db
```

Use a separate project-local database when testing manually:

```powershell
uv run echoes --db .\data\test.db import .\items.csv
uv run echoes --db .\data\test.db
```

So the usual local files are:

```text
data\echoes.db  # normal local use
data\test.db    # manual testing
```

Review progress is intentionally simple:

- each imported item starts at `0/3`;
- `Good` and `Easy` add one pass;
- `Hard` keeps the current pass count;
- `Again` resets the item to `0/3`;
- an item leaves the queue at `3/3`.

## Commands

```powershell
uv run echoes
uv run echoes import .\items.csv
uv run echoes stats
uv run echoes doctor
uv run echoes config get
uv run echoes config set boss_key f12
```

## Tests and Lint

```powershell
uv run pytest
uv run ruff check .
uv run ruff format . --check
```

Format files:

```powershell
uv run ruff format .
```

## Build Windows Portable Package

Build the onedir executable and zip package:

```powershell
.\scripts\build_windows.ps1
```

The output is:

```text
dist\Echoes-Windows\Echoes\
dist\Echoes-Windows-v0.1.0.zip
```

The portable package includes:

- `echoes.exe`
- `start.cmd`
- `import.cmd`
- `doctor.cmd`
- `items.csv.template`
- `README-quick.md`
- `data\`

The scripts set `ECHOES_HOME` to the local `data` folder so the package can be copied to another Windows device.

## Release Checklist

1. Run tests and lint.
2. Build the Windows package.
3. Test `doctor.cmd`.
4. Put a 60-item `items.csv` next to `import.cmd` and test import.
5. Test `start.cmd`.
6. Upload `dist\Echoes-Windows-v版本号.zip` to GitHub Releases.
