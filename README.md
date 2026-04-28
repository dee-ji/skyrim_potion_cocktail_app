# Skyrim Alchemy App

A real SQLite-backed version of the Skyrim Alchemy Tool.

## Run

```bash
uv sync
uv run fastapi dev app/main.py
```

Then open: http://127.0.0.1:8000

The database file is created at `app/skyrim_alchemy.db` by default.
Override with:

```bash
SKYRIM_ALCHEMY_DB=/path/to/skyrim_alchemy.db uv run fastapi dev app/main.py
```

## Query the database

```bash
sqlite3 app/skyrim_alchemy.db
.tables
.schema character_known_effects
SELECT * FROM characters;
```

The app also has a Database card with built-in read-only SELECT queries.
