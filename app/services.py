from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from app.rarity import rarity_for_ingredient


def ensure_character_exists(conn: sqlite3.Connection, character_id: int) -> None:
    if not conn.execute(
        "SELECT 1 FROM characters WHERE id=?", (character_id,)
    ).fetchone():
        raise HTTPException(404, "Character not found")


def get_ingredient_or_404(
    conn: sqlite3.Connection, ingredient_name: str, *, fields: str = "id, source"
) -> sqlite3.Row:
    ingredient = conn.execute(
        f"SELECT {fields} FROM ingredients WHERE name=?", (ingredient_name,)
    ).fetchone()
    if not ingredient:
        raise HTTPException(404, "Ingredient not found")
    return ingredient


def get_ingredient_effect_rows(
    conn: sqlite3.Connection, ingredient_id: int, effect_names: list[str]
) -> list[dict[str, int | str]]:
    placeholders = ",".join("?" for _ in effect_names)
    return [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT e.id, e.name
            FROM effects e
            JOIN ingredient_effects ie ON ie.effect_id = e.id
            WHERE ie.ingredient_id = ? AND e.name IN ({placeholders})
            """,
            (ingredient_id, *effect_names),
        ).fetchall()
    ]


def validate_ingredient_effects(
    conn: sqlite3.Connection, ingredient_id: int, effect_names: list[str]
) -> list[dict[str, int | str]]:
    effect_rows = get_ingredient_effect_rows(conn, ingredient_id, effect_names)
    if len(effect_rows) != len(set(effect_names)):
        raise HTTPException(400, "One or more effects do not belong to that ingredient")
    return effect_rows


def upsert_inventory_quantity(
    conn: sqlite3.Connection, character_id: int, ingredient_name: str, quantity: int
) -> dict[str, int | str]:
    ensure_character_exists(conn, character_id)
    ingredient = get_ingredient_or_404(conn, ingredient_name)
    conn.execute(
        """
        INSERT INTO character_inventory(character_id, ingredient_id, quantity, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(character_id, ingredient_id)
        DO UPDATE SET quantity = excluded.quantity, updated_at = CURRENT_TIMESTAMP
        """,
        (character_id, ingredient["id"], quantity),
    )
    return {
        "name": ingredient_name,
        "source": ingredient["source"],
        "quantity": quantity,
        **rarity_for_ingredient(ingredient_name),
    }
