# Skyrim Potion Cocktails

Skyrim Potion Cocktails is a FastAPI and SQLite app for tracking ingredient knowledge, managing character inventory, and finding the best potions to discover new effects.

It uses a single-page HTML/CSS/JavaScript UI backed by a small FastAPI API and a local SQLite database.

## Features

- Tracks `189` Skyrim ingredients across the base game, DLC, `_ResourcePack.esl`, several Creations, and quest-only sources.
- Shows ingredient source, rarity tier, and all four alchemy effects.
- Supports multiple characters with separate known effects and inventory.
- Lets you catch up progress by manually marking ingredient effects as known.
- Tracks per-character ingredient quantities and consumes inventory when a potion is marked as created.
- Finds discovery-focused potion combinations from your tracked inventory.
- Prioritizes recipes by discovery usefulness with rarity-aware scoring.
- Shows overall known-effect completion across all ingredients.
- Uses paged result rendering and cached lookups so large result lists stay more responsive.

## Stack

- `FastAPI`
- `SQLite`
- plain `HTML`, `CSS`, and `JavaScript`
- `uv` for dependency and dev-command management

## Requirements

- Python `3.11+`
- `uv`

## Install

```bash
uv sync
```

## Run The App

Start the development server from the project root:

```bash
uv run fastapi dev app/main.py
```

Then open:

- App UI: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`

The app initializes and seeds its SQLite database automatically on startup.

## Database Location

By default, the database file is created at:

```text
app/skyrim_alchemy.db
```

To override the database path:

```bash
SKYRIM_ALCHEMY_DB=/path/to/skyrim_alchemy.db uv run fastapi dev app/main.py
```

## How To Use

### 1. Create or select a character

- Use the `Characters` card to create a new character.
- Switch between characters to keep progress and inventory separate.

### 2. Review and filter ingredients

- Use the top filters to narrow ingredients by search text or source.
- The source filter supports base game, DLC, Creations, and quest-specific ingredient groups.

### 3. Check a direct recipe

- Use `Direct Recipe Check` to test a specific 2- or 3-ingredient recipe.
- Duplicate ingredient selection is blocked.

### 4. Track your inventory

- Use `Character Inventory` to add, remove, or set exact quantities.
- Click a tracked inventory row to load that ingredient into the inventory form for faster updates.

### 5. Discover new effects efficiently

- Use `Inventory Discovery Optimizer` to generate recipes from the ingredients you actually have.
- Select tracked ingredients manually, by current filter, or all at once.
- The results favor recipes that reveal more useful effects, especially on rarer ingredients.

### 6. Mark known effects manually

- Use `Catch Up Known Effects` to mark effects you already discovered in-game.
- Use this when the app needs to catch up to an existing save.

### 7. Mark a potion as created

- From the recipe results, click `Created` after crafting a potion.
- The app will:
  - mark matching effects as known for that character
  - reduce tracked inventory quantities
  - remove recipes that are no longer possible when an ingredient drops to `0`

### 8. Track overall completion

- The `Known Effects` card shows:
  - total known effects
  - total possible effects
  - completion percentage
  - fully solved ingredients

## API Overview

Main endpoints:

- `GET /api/ingredients`
- `GET /api/characters`
- `POST /api/characters`
- `DELETE /api/characters/{character_id}`
- `GET /api/characters/{character_id}/inventory`
- `PUT /api/characters/{character_id}/inventory`
- `POST /api/characters/{character_id}/inventory/adjust`
- `GET /api/characters/{character_id}/known-effects`
- `POST /api/characters/{character_id}/known-effects`
- `DELETE /api/characters/{character_id}/known-effects`
- `POST /api/characters/{character_id}/created-recipes`

See `/docs` for the full OpenAPI schema and request/response models.

## Development

Run the test suite:

```bash
uv run pytest -q
```

Syntax-check key backend modules:

```bash
python3 -m py_compile app/main.py app/app_factory.py app/routes/*.py app/services.py app/db.py
```

## Project Structure

```text
app/
  app_factory.py      FastAPI app setup
  config.py           Paths and app configuration
  db.py               SQLite setup and seed logic
  main.py             Compatibility entrypoint
  rarity.py           Rarity tier metadata
  routes/
    characters.py     Character, inventory, and recipe routes
    ingredients.py    Ingredient API
    pages.py          UI page route
  static/
    index.html        Single-page app UI
  data/
    ingredients.json  Ingredient source data
tests/
  test_api.py
```

## Notes

- The UI is intentionally framework-free and lives in a single HTML file.
- The backend uses parameterized SQL queries throughout the API paths.
- Inventory, known effects, and created recipe behavior are persisted in SQLite.
