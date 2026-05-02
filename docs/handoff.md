# Handoff

## What This Repo Is

This repo contains the current production baseline for Skyrim Potion Cocktails:

- FastAPI backend
- SQLite persistence
- single-page HTML/CSS/JavaScript frontend
- Skyrim ingredient dataset with source labels
- rarity metadata
- discovery ranking and inventory behavior

It is the best current expression of the project's alchemy rules and user workflow.

## What Must Be Preserved

If a new repo is created for a Skyrim mod, companion app, or packaged desktop build, these behaviors should be treated as intentional unless explicitly redesigned:

- each ingredient has 4 ordered effects
- ingredient names are unique
- ingredient source labels are meaningful and user-facing
- rarity is distinct from known-effect status
- recipe discovery ranking is rarity-aware
- using a rarer ingredient only to unlock lower-rarity ingredients should be deprioritized
- when other conditions are equal, fewer ingredients should be preferred
- character inventory is authoritative for inventory-based recipe generation
- crafting a recipe can consume one of each ingredient and update known effects

## Authoritative Files

- `app/data/ingredients.json`
  - ingredient names, sources, effects
- `app/rarity.py`
  - rarity tiers and notes
- `app/routes/characters.py`
  - inventory and known-effect semantics
- `app/static/index.html`
  - current UI workflows and discovery UX
- `tests/test_api.py`
  - backend behavior currently verified by tests

## Current Feature Summary

- `189` ingredients are supported
- sources include base Skyrim, DLC, `_ResourcePack.esl`, multiple Creations, and quest-only sources
- per-character inventory tracking exists
- per-character known-effect tracking exists
- manual catch-up for known effects exists
- direct recipe checking exists
- inventory-based discovery optimization exists
- rarity-aware discovery sorting exists
- known-effect completion metrics exist

## What A Future Mod Repo Should Reuse

At minimum, a future Skyrim mod repo should inherit:

- ingredient dataset
- source labels
- rarity tiers
- discovery scoring intent
- inventory semantics
- known-effect semantics

The mod repo should not rediscover these rules ad hoc.

## Recommended Split

Keep this repo as:

- domain and product baseline
- web app implementation
- easiest place to evolve alchemy logic

Use the future mod repo as:

- Skyrim-specific integration layer
- packaging and distribution layer
- Creation Kit / Papyrus / SKSE experiments if needed

## Recommended Handoff Assets

When work begins in the mod repo, copy or derive:

- `AGENTS.md` guidance
- this handoff document
- `docs/discovery-scoring.md`
- exported ingredient/source/rarity data if a dedicated export format is added later

## Non-Goals For The Mod Repo

Avoid starting by rewriting everything as an in-game UI clone.

The lowest-risk first product is likely:

- a PC companion build for Skyrim players
- or a very small in-game integration layer on top of a companion app

## Change Management

If the mod repo intentionally diverges from this repo:

- document the divergence explicitly
- explain whether the change is due to gameplay constraints, UI constraints, or Skyrim engine constraints
- do not silently fork the meaning of rarity, discovery priority, or inventory consumption
