# Draft AGENTS.md For Future Skyrim Mod Repo

## Purpose

This repository builds a Skyrim PC mod or companion experience derived from the Skyrim Potion Cocktails app.

The original web app repo is the current domain baseline for ingredient data, rarity, discovery logic, and inventory behavior. This repo should preserve those semantics unless a documented reason exists to diverge.

## Relationship To The Source App

The source app repo provides the current authoritative baseline for:

- ingredient names
- source labels
- ordered effects
- rarity tiers
- discovery ranking intent
- inventory and known-effect workflows

Do not re-derive these rules informally from memory.

## Primary Goals

- adapt the Skyrim Potion Cocktails domain model into a Skyrim PC mod or companion-tool format
- remain maintainable
- keep compatibility with the source app's logic where feasible
- document any divergence caused by Skyrim engine, UI, or modding constraints

## Source Of Truth

Until replaced by an explicit shared-core package or export pipeline, the authoritative baseline is the original app repo:

- `app/data/ingredients.json`
- `app/rarity.py`
- `docs/handoff.md`
- `docs/discovery-scoring.md`
- `AGENTS.md`

## Implementation Priorities

- prefer incremental integration over full rewrites
- keep Skyrim-specific code and shared domain rules conceptually separate
- if building a companion app first, reuse as much existing behavior as possible
- if building an in-game mod, start with a narrow scope and clear dependencies

## Expected Constraints

- Skyrim UI and scripting capabilities are more limited than a browser app
- feature parity with the web app may require staged delivery
- some workflows may need to be simplified for Papyrus, SkyUI, or Creation Kit realities

## Do Not Do

- do not silently change rarity semantics
- do not silently change discovery ranking goals
- do not duplicate large datasets manually if exported data can be consumed instead
- do not treat the mod repo as a clean-slate redesign unless the user explicitly wants that

## When In Doubt

- preserve behavior
- document divergence
- prefer maintainability
- ask whether the goal is gameplay fidelity, UI fidelity, or engineering simplicity
