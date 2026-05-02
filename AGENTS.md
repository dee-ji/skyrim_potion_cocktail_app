# AGENTS.md

## Purpose

This repository is the authoritative source for the current Skyrim Potion Cocktails application: a FastAPI, SQLite, and plain HTML/CSS/JavaScript tool for Skyrim alchemy planning.

Agents working in this repo should preserve the app's domain behavior unless the user explicitly asks to change it.

## Primary Goals

- Track Skyrim alchemy ingredients, effects, rarity, and source metadata.
- Track per-character known effects and ingredient inventory.
- Help the user discover the most useful potion combinations.
- Prefer maintainable, readable solutions over clever abstractions.

## Source Of Truth

The following assets are the current domain baseline:

- `app/data/ingredients.json`
  - authoritative ingredient list, source label, and ordered effect slots
- `app/rarity.py`
  - authoritative rarity tiers and rarity notes
- `app/static/index.html`
  - authoritative UI behavior and current user workflow
- `app/routes/characters.py`
  - authoritative inventory, known-effect, and created-recipe API behavior

If behavior changes in one layer, keep the other layers aligned.

## Domain Rules

- Each ingredient has exactly 4 effects in a fixed order.
- Ingredient names are unique within the app.
- Source labels should remain explicit and user-facing.
- Rarity is a separate concern from known/unknown effect state.
- Discovery ranking should favor unlocking useful effects on rarer ingredients.
- Inventory is tracked per character.
- Marking a potion as created should:
  - mark discovered effects for matching ingredients
  - consume tracked inventory when enabled
  - update result validity when ingredients drop to `0`
- Duplicate ingredients should not be treated as valid in direct recipe checks.

## API And Backend Guidance

- Use parameterized SQL queries only.
- Keep FastAPI code modern and small.
- Prefer typed Pydantic request and response models.
- Reuse shared helper functions instead of duplicating lookup logic.
- Preserve local SQLite simplicity unless the user asks for a larger architecture change.

## Frontend Guidance

- Keep the app framework-free unless the user explicitly requests otherwise.
- Preserve the existing Elder Scrolls / Arcane Laboratory theme unless asked to restyle it.
- Do not regress performance on large recipe result sets.
- Favor direct, understandable DOM code over abstract UI helpers.

## Mod Handoff Context

This repo is also the design baseline for a future Skyrim mod or companion-tool repo.

When preparing content for that future repo:

- preserve ingredient/effect/source/rarity semantics
- preserve discovery scoring intent
- document any deliberate divergence from this app
- prefer exporting structured data over re-deriving rules by hand

See:

- `docs/handoff.md`
- `docs/discovery-scoring.md`
- `docs/skyrim-mod-repo-AGENTS.draft.md`

## Working Style

- Make focused changes.
- Keep docs aligned with behavior.
- Do not silently change domain rules.
- When in doubt, ask whether the user wants a gameplay-rule change or just a UI/implementation change.
