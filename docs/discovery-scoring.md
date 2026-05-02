# Discovery Scoring

## Purpose

The app does not rank recipes only by potion value. It tries to help the user discover the most useful unknown effects with limited inventory, especially for rare ingredients.

## Core Intent

Discovery ranking should:

- prioritize revealing unknown effects
- give extra weight to rarer ingredients
- prefer revealing multiple effects on the same rare ingredient over spending that ingredient inefficiently
- avoid wasting a rarer ingredient just to reveal lower-rarity ingredient effects
- use estimated value as a secondary tie-break
- prefer fewer ingredients when higher-priority factors are tied

## Expected Behavior

Examples of intended ranking behavior:

- a recipe that reveals 2 effects on `Hagraven Feathers` should rank above one that reveals only 1 effect on `Hagraven Feathers` when other factors are comparable
- a recipe that spends a `Rare` ingredient only to discover `Common` effects should be pushed down
- a 2-ingredient recipe should beat a 3-ingredient recipe when discovery priority and value are otherwise tied

## Discovery Inputs

The ranking logic depends on:

- which effects are currently known for the active character
- ingredient rarity
- which ingredients are present in tracked inventory
- the estimated potion value
- how many ingredients the recipe consumes

## Important Distinctions

- Rarity display is a separate visual system from known/unknown effect status.
- Direct recipe validation and discovery ranking are separate concerns.
- Alphabetical ingredient display in results is a usability choice and should not be confused with ranking order.

## If Ported To Another Repo

If this logic is reimplemented elsewhere:

- preserve the ranking intent first
- preserve rare-ingredient protection behavior
- preserve value as a secondary sort signal
- preserve ingredient-count minimization as a later tie-break

If exact numeric formulas change, the behavior should still match these user-facing goals.
