from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from app.rarity import rarity_for_ingredient
except ModuleNotFoundError:
    from rarity import rarity_for_ingredient

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("SKYRIM_ALCHEMY_DB", BASE_DIR / "skyrim_alchemy.db"))
DATA_PATH = BASE_DIR / "data" / "ingredients.json"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Skyrim Alchemy API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rows(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(r) for r in cur.fetchall()]


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS effects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                polarity TEXT NOT NULL CHECK (polarity IN ('positive','negative','mixed')) DEFAULT 'mixed'
            );

            CREATE TABLE IF NOT EXISTS ingredient_effects (
                ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
                effect_id INTEGER NOT NULL REFERENCES effects(id) ON DELETE CASCADE,
                slot INTEGER NOT NULL CHECK (slot BETWEEN 1 AND 4),
                PRIMARY KEY (ingredient_id, effect_id),
                UNIQUE (ingredient_id, slot)
            );

            CREATE TABLE IF NOT EXISTS character_known_effects (
                character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
                effect_id INTEGER NOT NULL REFERENCES effects(id) ON DELETE CASCADE,
                discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, ingredient_id, effect_id)
            );

            CREATE TABLE IF NOT EXISTS character_inventory (
                character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
                quantity INTEGER NOT NULL CHECK (quantity >= 0) DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (character_id, ingredient_id)
            );

            CREATE TABLE IF NOT EXISTS created_recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                ingredient_names TEXT NOT NULL,
                effect_names TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        seed(conn)


def seed(conn: sqlite3.Connection) -> None:
    ingredients = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    positive = {
        "Cure Disease",
        "Fortify Alteration",
        "Fortify Barter",
        "Fortify Block",
        "Fortify Carry Weight",
        "Fortify Conjuration",
        "Fortify Destruction",
        "Fortify Enchanting",
        "Fortify Health",
        "Fortify Heavy Armor",
        "Fortify Illusion",
        "Fortify Light Armor",
        "Fortify Lockpicking",
        "Fortify Magicka",
        "Fortify Marksman",
        "Fortify One-handed",
        "Fortify Pickpocket",
        "Fortify Restoration",
        "Fortify Smithing",
        "Fortify Sneak",
        "Fortify Stamina",
        "Fortify Two-handed",
        "Invisibility",
        "Paralysis",
        "Regenerate Health",
        "Regenerate Magicka",
        "Regenerate Stamina",
        "Resist Fire",
        "Resist Frost",
        "Resist Magic",
        "Resist Poison",
        "Resist Shock",
        "Restore Health",
        "Restore Magicka",
        "Restore Stamina",
        "Waterbreathing",
    }
    negative = {
        "Damage Health",
        "Damage Magicka",
        "Damage Magicka Regen",
        "Damage Stamina",
        "Damage Stamina Regen",
        "Fear",
        "Frenzy",
        "Lingering Damage Health",
        "Lingering Damage Magicka",
        "Lingering Damage Stamina",
        "Ravage Health",
        "Ravage Magicka",
        "Ravage Stamina",
        "Slow",
        "Weakness to Fire",
        "Weakness to Frost",
        "Weakness to Magic",
        "Weakness to Poison",
        "Weakness to Shock",
    }
    for item in ingredients:
        conn.execute(
            "INSERT OR IGNORE INTO ingredients(name, source) VALUES (?, ?)",
            (item["name"], item["source"]),
        )
        ingredient_id = conn.execute(
            "SELECT id FROM ingredients WHERE name=?", (item["name"],)
        ).fetchone()["id"]
        for idx, effect in enumerate(item["effects"], start=1):
            polarity = (
                "positive"
                if effect in positive
                else "negative"
                if effect in negative
                else "mixed"
            )
            conn.execute(
                "INSERT OR IGNORE INTO effects(name, polarity) VALUES (?, ?)",
                (effect, polarity),
            )
            effect_id = conn.execute(
                "SELECT id FROM effects WHERE name=?", (effect,)
            ).fetchone()["id"]
            conn.execute(
                "INSERT OR IGNORE INTO ingredient_effects(ingredient_id, effect_id, slot) VALUES (?, ?, ?)",
                (ingredient_id, effect_id, idx),
            )


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/ingredients")
def ingredients() -> dict[str, Any]:
    with db() as conn:
        data = rows(
            conn.execute(
                """
            SELECT i.id, i.name, i.source, json_group_array(e.name ORDER BY ie.slot) AS effects
            FROM ingredients i
            JOIN ingredient_effects ie ON ie.ingredient_id = i.id
            JOIN effects e ON e.id = ie.effect_id
            GROUP BY i.id
            ORDER BY i.name
            """
            )
        )
    for item in data:
        item["effects"] = json.loads(item["effects"])
        item.update(rarity_for_ingredient(item["name"]))
    return {"ingredients": data}


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


@app.get("/api/characters")
def list_characters(q: str = "") -> dict[str, Any]:
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
    return {"characters": data}


@app.post("/api/characters")
def create_character(payload: CharacterCreate) -> dict[str, Any]:
    try:
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO characters(name) VALUES (?)", (payload.name.strip(),)
            )
            char = dict(
                conn.execute(
                    "SELECT * FROM characters WHERE id=?", (cur.lastrowid,)
                ).fetchone()
            )
        return {"character": char}
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Character already exists")


@app.delete("/api/characters/{character_id}")
def delete_character(character_id: int) -> dict[str, Any]:
    with db() as conn:
        conn.execute("DELETE FROM characters WHERE id=?", (character_id,))
    return {"ok": True}


@app.get("/api/characters/{character_id}/known-effects")
def known_effects(character_id: int) -> dict[str, Any]:
    with db() as conn:
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
    return {"known_effects": data}


@app.get("/api/characters/{character_id}/inventory")
def get_inventory(character_id: int) -> dict[str, Any]:
    with db() as conn:
        if not conn.execute(
            "SELECT 1 FROM characters WHERE id=?", (character_id,)
        ).fetchone():
            raise HTTPException(404, "Character not found")
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
    return {"inventory": data}


class InventoryUpdate(BaseModel):
    ingredient_name: str = Field(min_length=1)
    quantity: int = Field(ge=0)


class InventoryAdjust(BaseModel):
    ingredient_name: str = Field(min_length=1)
    delta: int


def update_inventory_quantity(
    conn: sqlite3.Connection, character_id: int, ingredient_name: str, quantity: int
) -> dict[str, Any]:
    if not conn.execute(
        "SELECT 1 FROM characters WHERE id=?", (character_id,)
    ).fetchone():
        raise HTTPException(404, "Character not found")
    ingredient = conn.execute(
        "SELECT id, source FROM ingredients WHERE name=?", (ingredient_name,)
    ).fetchone()
    if not ingredient:
        raise HTTPException(404, "Ingredient not found")
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
        "ingredient": ingredient_name,
        "source": ingredient["source"],
        "quantity": quantity,
        **rarity_for_ingredient(ingredient_name),
    }


@app.put("/api/characters/{character_id}/inventory")
def set_inventory_item(character_id: int, payload: InventoryUpdate) -> dict[str, Any]:
    with db() as conn:
        item = update_inventory_quantity(
            conn, character_id, payload.ingredient_name, payload.quantity
        )
    return {"ok": True, "item": item}


@app.post("/api/characters/{character_id}/inventory/adjust")
def adjust_inventory_item(
    character_id: int, payload: InventoryAdjust
) -> dict[str, Any]:
    with db() as conn:
        if not conn.execute(
            "SELECT 1 FROM characters WHERE id=?", (character_id,)
        ).fetchone():
            raise HTTPException(404, "Character not found")
        ingredient = conn.execute(
            "SELECT id, source FROM ingredients WHERE name=?",
            (payload.ingredient_name,),
        ).fetchone()
        if not ingredient:
            raise HTTPException(404, "Ingredient not found")
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
        item = update_inventory_quantity(
            conn, character_id, payload.ingredient_name, next_quantity
        )
    return {"ok": True, "item": item}


class KnownEffectsUpdate(BaseModel):
    ingredient_name: str = Field(min_length=1)
    effect_names: list[str] = Field(min_length=1)


@app.post("/api/characters/{character_id}/known-effects")
def add_known_effects(character_id: int, payload: KnownEffectsUpdate) -> dict[str, Any]:
    with db() as conn:
        if not conn.execute(
            "SELECT 1 FROM characters WHERE id=?", (character_id,)
        ).fetchone():
            raise HTTPException(404, "Character not found")
        ingredient = conn.execute(
            "SELECT id FROM ingredients WHERE name=?", (payload.ingredient_name,)
        ).fetchone()
        if not ingredient:
            raise HTTPException(404, "Ingredient not found")
        placeholders = ",".join("?" for _ in payload.effect_names)
        effect_rows = rows(
            conn.execute(
                f"""
            SELECT e.id, e.name
            FROM effects e
            JOIN ingredient_effects ie ON ie.effect_id = e.id
            WHERE ie.ingredient_id = ? AND e.name IN ({placeholders})
            """,
                (ingredient["id"], *payload.effect_names),
            )
        )
        if len(effect_rows) != len(set(payload.effect_names)):
            raise HTTPException(
                400, "One or more effects do not belong to that ingredient"
            )
        before_changes = conn.total_changes
        for effect in effect_rows:
            conn.execute(
                "INSERT OR IGNORE INTO character_known_effects(character_id, ingredient_id, effect_id) VALUES (?, ?, ?)",
                (character_id, ingredient["id"], effect["id"]),
            )
        return {"ok": True, "marked": conn.total_changes - before_changes}


@app.delete("/api/characters/{character_id}/known-effects")
def remove_known_effects(
    character_id: int, payload: KnownEffectsUpdate
) -> dict[str, Any]:
    with db() as conn:
        if not conn.execute(
            "SELECT 1 FROM characters WHERE id=?", (character_id,)
        ).fetchone():
            raise HTTPException(404, "Character not found")
        ingredient = conn.execute(
            "SELECT id FROM ingredients WHERE name=?", (payload.ingredient_name,)
        ).fetchone()
        if not ingredient:
            raise HTTPException(404, "Ingredient not found")
        placeholders = ",".join("?" for _ in payload.effect_names)
        effect_rows = rows(
            conn.execute(
                f"""
            SELECT e.id, e.name
            FROM effects e
            JOIN ingredient_effects ie ON ie.effect_id = e.id
            WHERE ie.ingredient_id = ? AND e.name IN ({placeholders})
            """,
                (ingredient["id"], *payload.effect_names),
            )
        )
        if len(effect_rows) != len(set(payload.effect_names)):
            raise HTTPException(
                400, "One or more effects do not belong to that ingredient"
            )
        before_changes = conn.total_changes
        conn.execute(
            f"""
            DELETE FROM character_known_effects
            WHERE character_id = ? AND ingredient_id = ? AND effect_id IN ({",".join("?" for _ in effect_rows)})
            """,
            (character_id, ingredient["id"], *(effect["id"] for effect in effect_rows)),
        )
        return {"ok": True, "removed": conn.total_changes - before_changes}


class CreatedRecipe(BaseModel):
    ingredient_names: list[str]
    effect_names: list[str]
    consume_inventory: bool = True


@app.post("/api/characters/{character_id}/created-recipes")
def mark_created(character_id: int, payload: CreatedRecipe) -> dict[str, Any]:
    if len(payload.ingredient_names) not in (2, 3):
        raise HTTPException(400, "Recipe must have 2 or 3 ingredients")
    with db() as conn:
        if not conn.execute(
            "SELECT 1 FROM characters WHERE id=?", (character_id,)
        ).fetchone():
            raise HTTPException(404, "Character not found")
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
        ingredient_by_name = {r["name"]: r["id"] for r in ingredient_ids}
        effect_by_name = {r["name"]: r["id"] for r in effect_ids}
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
        inserted = 0
        for ing_name in payload.ingredient_names:
            for eff_name in payload.effect_names:
                if ing_name in ingredient_by_name and eff_name in effect_by_name:
                    has_effect = conn.execute(
                        "SELECT 1 FROM ingredient_effects WHERE ingredient_id=? AND effect_id=?",
                        (ingredient_by_name[ing_name], effect_by_name[eff_name]),
                    ).fetchone()
                    if has_effect:
                        conn.execute(
                            "INSERT OR IGNORE INTO character_known_effects(character_id, ingredient_id, effect_id) VALUES (?, ?, ?)",
                            (
                                character_id,
                                ingredient_by_name[ing_name],
                                effect_by_name[eff_name],
                            ),
                        )
                        inserted += conn.total_changes
        if payload.consume_inventory:
            for ing_name, required in ingredient_counts.items():
                conn.execute(
                    """
                    INSERT INTO character_inventory(character_id, ingredient_id, quantity, updated_at)
                    VALUES (?, ?, 0, CURRENT_TIMESTAMP)
                    ON CONFLICT(character_id, ingredient_id)
                    DO UPDATE SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP
                    """,
                    (character_id, ingredient_by_name[ing_name], required),
                )
        conn.execute(
            "INSERT INTO created_recipes(character_id, ingredient_names, effect_names) VALUES (?, ?, ?)",
            (
                character_id,
                json.dumps(payload.ingredient_names),
                json.dumps(payload.effect_names),
            ),
        )
        remaining_inventory = rows(
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
    return {"ok": True, "marked": inserted, "inventory": remaining_inventory}


@app.get("/api/debug/query")
def debug_query(sql: str = Query(..., min_length=1)) -> dict[str, Any]:
    if not sql.lstrip().lower().startswith("select"):
        raise HTTPException(400, "Only SELECT queries are allowed from the browser")
    with db() as conn:
        try:
            cur = conn.execute(sql)
            return {"columns": [d[0] for d in cur.description or []], "rows": rows(cur)}
        except sqlite3.Error as e:
            raise HTTPException(400, str(e))
