from __future__ import annotations

import json
import sqlite3
from collections import Counter

from fastapi import APIRouter, HTTPException

from app.db import db, rows
from app.rarity import rarity_for_ingredient
from app.schemas import (
    CharacterCreate,
    CharacterOut,
    CharacterResponse,
    CharactersResponse,
    CreatedRecipe,
    CreatedRecipeResponse,
    InventoryAdjust,
    InventoryItemOut,
    InventoryMutationResponse,
    InventoryResponse,
    InventoryUpdate,
    KnownEffectOut,
    KnownEffectsMutationResponse,
    KnownEffectsResponse,
    KnownEffectsUpdate,
    OkResponse,
    RecipeInventoryItemOut,
)
from app.services import (
    ensure_character_exists,
    get_ingredient_or_404,
    upsert_inventory_quantity,
    validate_ingredient_effects,
)

router = APIRouter(tags=["characters"])


@router.get("/api/characters", response_model=CharactersResponse)
def list_characters(q: str = "") -> CharactersResponse:
    with db() as conn:
        if q:
            data = rows(
                conn.execute(
                    "SELECT * FROM characters WHERE name LIKE ? ORDER BY name",
                    (f"%{q}%",),
                )
            )
        else:
            data = rows(conn.execute("SELECT * FROM characters ORDER BY name"))
    return CharactersResponse(
        characters=[CharacterOut.model_validate(item) for item in data]
    )


@router.post("/api/characters", response_model=CharacterResponse)
def create_character(payload: CharacterCreate) -> CharacterResponse:
    try:
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO characters(name) VALUES (?)", (payload.name.strip(),)
            )
            character = dict(
                conn.execute(
                    "SELECT * FROM characters WHERE id=?", (cur.lastrowid,)
                ).fetchone()
            )
        return CharacterResponse(character=CharacterOut.model_validate(character))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Character already exists") from exc


@router.delete("/api/characters/{character_id}", response_model=OkResponse)
def delete_character(character_id: int) -> OkResponse:
    with db() as conn:
        conn.execute("DELETE FROM characters WHERE id=?", (character_id,))
    return OkResponse()


@router.get(
    "/api/characters/{character_id}/known-effects", response_model=KnownEffectsResponse
)
def known_effects(character_id: int) -> KnownEffectsResponse:
    with db() as conn:
        ensure_character_exists(conn, character_id)
        data = rows(
            conn.execute(
                """
                SELECT i.name AS ingredient, e.name AS effect, cke.discovered_at
                FROM character_known_effects cke
                JOIN ingredients i ON i.id = cke.ingredient_id
                JOIN effects e ON e.id = cke.effect_id
                WHERE cke.character_id=?
                ORDER BY i.name, e.name
                """,
                (character_id,),
            )
        )
    return KnownEffectsResponse(
        known_effects=[KnownEffectOut.model_validate(item) for item in data]
    )


@router.get(
    "/api/characters/{character_id}/inventory", response_model=InventoryResponse
)
def get_inventory(character_id: int) -> InventoryResponse:
    with db() as conn:
        ensure_character_exists(conn, character_id)
        data = rows(
            conn.execute(
                """
                SELECT i.name, i.source, ci.quantity
                FROM character_inventory ci
                JOIN ingredients i ON i.id = ci.ingredient_id
                WHERE ci.character_id = ? AND ci.quantity > 0
                ORDER BY ci.quantity DESC, i.name
                """,
                (character_id,),
            )
        )
    for item in data:
        item.update(rarity_for_ingredient(item["name"]))
    return InventoryResponse(
        inventory=[InventoryItemOut.model_validate(item) for item in data]
    )


@router.put(
    "/api/characters/{character_id}/inventory", response_model=InventoryMutationResponse
)
def set_inventory_item(
    character_id: int, payload: InventoryUpdate
) -> InventoryMutationResponse:
    with db() as conn:
        item = upsert_inventory_quantity(
            conn, character_id, payload.ingredient_name, payload.quantity
        )
    return InventoryMutationResponse(item=InventoryItemOut.model_validate(item))


@router.post(
    "/api/characters/{character_id}/inventory/adjust",
    response_model=InventoryMutationResponse,
)
def adjust_inventory_item(
    character_id: int, payload: InventoryAdjust
) -> InventoryMutationResponse:
    with db() as conn:
        ensure_character_exists(conn, character_id)
        ingredient = get_ingredient_or_404(conn, payload.ingredient_name)
        row = conn.execute(
            "SELECT quantity FROM character_inventory WHERE character_id=? AND ingredient_id=?",
            (character_id, ingredient["id"]),
        ).fetchone()
        current_quantity = row["quantity"] if row else 0
        next_quantity = current_quantity + payload.delta
        if next_quantity < 0:
            raise HTTPException(
                400, f"Not enough {payload.ingredient_name} in inventory"
            )
        item = upsert_inventory_quantity(
            conn, character_id, payload.ingredient_name, next_quantity
        )
    return InventoryMutationResponse(item=InventoryItemOut.model_validate(item))


@router.post(
    "/api/characters/{character_id}/known-effects",
    response_model=KnownEffectsMutationResponse,
)
def add_known_effects(
    character_id: int, payload: KnownEffectsUpdate
) -> KnownEffectsMutationResponse:
    with db() as conn:
        ensure_character_exists(conn, character_id)
        ingredient = get_ingredient_or_404(conn, payload.ingredient_name, fields="id")
        effect_rows = validate_ingredient_effects(
            conn, ingredient["id"], payload.effect_names
        )
        before_changes = conn.total_changes
        for effect in effect_rows:
            conn.execute(
                "INSERT OR IGNORE INTO character_known_effects(character_id, ingredient_id, effect_id) VALUES (?, ?, ?)",
                (character_id, ingredient["id"], effect["id"]),
            )
        marked = conn.total_changes - before_changes
    return KnownEffectsMutationResponse(marked=marked)


@router.delete(
    "/api/characters/{character_id}/known-effects",
    response_model=KnownEffectsMutationResponse,
)
def remove_known_effects(
    character_id: int, payload: KnownEffectsUpdate
) -> KnownEffectsMutationResponse:
    with db() as conn:
        ensure_character_exists(conn, character_id)
        ingredient = get_ingredient_or_404(conn, payload.ingredient_name, fields="id")
        effect_rows = validate_ingredient_effects(
            conn, ingredient["id"], payload.effect_names
        )
        before_changes = conn.total_changes
        conn.execute(
            f"""
            DELETE FROM character_known_effects
            WHERE character_id = ? AND ingredient_id = ? AND effect_id IN ({",".join("?" for _ in effect_rows)})
            """,
            (character_id, ingredient["id"], *(effect["id"] for effect in effect_rows)),
        )
        removed = conn.total_changes - before_changes
    return KnownEffectsMutationResponse(removed=removed)


@router.post(
    "/api/characters/{character_id}/created-recipes",
    response_model=CreatedRecipeResponse,
)
def mark_created(character_id: int, payload: CreatedRecipe) -> CreatedRecipeResponse:
    if len(payload.ingredient_names) not in (2, 3):
        raise HTTPException(400, "Recipe must have 2 or 3 ingredients")
    with db() as conn:
        ensure_character_exists(conn, character_id)
        ingredient_ids = rows(
            conn.execute(
                f"SELECT id, name FROM ingredients WHERE name IN ({','.join('?' for _ in payload.ingredient_names)})",
                payload.ingredient_names,
            )
        )
        effect_ids = rows(
            conn.execute(
                f"SELECT id, name FROM effects WHERE name IN ({','.join('?' for _ in payload.effect_names)})",
                payload.effect_names,
            )
        )
        ingredient_by_name = {row["name"]: row["id"] for row in ingredient_ids}
        effect_by_name = {row["name"]: row["id"] for row in effect_ids}
        ingredient_counts = Counter(payload.ingredient_names)
        if len(ingredient_by_name) != len(ingredient_counts):
            raise HTTPException(400, "One or more ingredients were not found")
        if payload.consume_inventory:
            inventory_rows = rows(
                conn.execute(
                    f"""
                    SELECT i.name, ci.quantity
                    FROM character_inventory ci
                    JOIN ingredients i ON i.id = ci.ingredient_id
                    WHERE ci.character_id = ? AND i.name IN ({",".join("?" for _ in ingredient_counts)})
                    """,
                    (character_id, *ingredient_counts.keys()),
                )
            )
            quantities_by_name = {
                row["name"]: row["quantity"] for row in inventory_rows
            }
            missing = [
                f"{name} ({quantities_by_name.get(name, 0)}/{required})"
                for name, required in ingredient_counts.items()
                if quantities_by_name.get(name, 0) < required
            ]
            if missing:
                raise HTTPException(400, "Not enough inventory: " + ", ".join(missing))
        marked = 0
        for ingredient_name in payload.ingredient_names:
            for effect_name in payload.effect_names:
                if (
                    ingredient_name not in ingredient_by_name
                    or effect_name not in effect_by_name
                ):
                    continue
                has_effect = conn.execute(
                    "SELECT 1 FROM ingredient_effects WHERE ingredient_id=? AND effect_id=?",
                    (ingredient_by_name[ingredient_name], effect_by_name[effect_name]),
                ).fetchone()
                if has_effect:
                    before_changes = conn.total_changes
                    conn.execute(
                        "INSERT OR IGNORE INTO character_known_effects(character_id, ingredient_id, effect_id) VALUES (?, ?, ?)",
                        (
                            character_id,
                            ingredient_by_name[ingredient_name],
                            effect_by_name[effect_name],
                        ),
                    )
                    marked += conn.total_changes - before_changes
        if payload.consume_inventory:
            for ingredient_name, required in ingredient_counts.items():
                conn.execute(
                    """
                    INSERT INTO character_inventory(character_id, ingredient_id, quantity, updated_at)
                    VALUES (?, ?, 0, CURRENT_TIMESTAMP)
                    ON CONFLICT(character_id, ingredient_id)
                    DO UPDATE SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP
                    """,
                    (character_id, ingredient_by_name[ingredient_name], required),
                )
        conn.execute(
            "INSERT INTO created_recipes(character_id, ingredient_names, effect_names) VALUES (?, ?, ?)",
            (
                character_id,
                json.dumps(payload.ingredient_names),
                json.dumps(payload.effect_names),
            ),
        )
        inventory = rows(
            conn.execute(
                f"""
                SELECT i.name, ci.quantity
                FROM character_inventory ci
                JOIN ingredients i ON i.id = ci.ingredient_id
                WHERE ci.character_id = ? AND i.name IN ({",".join("?" for _ in ingredient_counts)})
                """,
                (character_id, *ingredient_counts.keys()),
            )
        )
    return CreatedRecipeResponse(
        marked=marked,
        inventory=[RecipeInventoryItemOut.model_validate(item) for item in inventory],
    )
