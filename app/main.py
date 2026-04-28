from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("SKYRIM_ALCHEMY_DB", BASE_DIR / "skyrim_alchemy.db"))
DATA_PATH = BASE_DIR / "data" / "ingredients.json"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Skyrim Alchemy API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
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
        "Cure Disease","Fortify Alteration","Fortify Barter","Fortify Block","Fortify Carry Weight","Fortify Conjuration",
        "Fortify Destruction","Fortify Enchanting","Fortify Health","Fortify Heavy Armor","Fortify Illusion","Fortify Light Armor",
        "Fortify Lockpicking","Fortify Magicka","Fortify Marksman","Fortify One-handed","Fortify Pickpocket","Fortify Restoration",
        "Fortify Smithing","Fortify Sneak","Fortify Stamina","Fortify Two-handed","Invisibility","Paralysis","Regenerate Health",
        "Regenerate Magicka","Regenerate Stamina","Resist Fire","Resist Frost","Resist Magic","Resist Poison","Resist Shock",
        "Restore Health","Restore Magicka","Restore Stamina","Waterbreathing"
    }
    negative = {
        "Damage Health","Damage Magicka","Damage Magicka Regen","Damage Stamina","Damage Stamina Regen","Fear","Frenzy",
        "Lingering Damage Health","Lingering Damage Magicka","Lingering Damage Stamina","Ravage Health","Ravage Magicka",
        "Ravage Stamina","Slow","Weakness to Fire","Weakness to Frost","Weakness to Magic","Weakness to Poison","Weakness to Shock"
    }
    for item in ingredients:
        conn.execute("INSERT OR IGNORE INTO ingredients(name, source) VALUES (?, ?)", (item["name"], item["source"]))
        ingredient_id = conn.execute("SELECT id FROM ingredients WHERE name=?", (item["name"],)).fetchone()["id"]
        for idx, effect in enumerate(item["effects"], start=1):
            polarity = "positive" if effect in positive else "negative" if effect in negative else "mixed"
            conn.execute("INSERT OR IGNORE INTO effects(name, polarity) VALUES (?, ?)", (effect, polarity))
            effect_id = conn.execute("SELECT id FROM effects WHERE name=?", (effect,)).fetchone()["id"]
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
        data = rows(conn.execute(
            """
            SELECT i.id, i.name, i.source, json_group_array(e.name ORDER BY ie.slot) AS effects
            FROM ingredients i
            JOIN ingredient_effects ie ON ie.ingredient_id = i.id
            JOIN effects e ON e.id = ie.effect_id
            GROUP BY i.id
            ORDER BY i.name
            """
        ))
    for item in data:
        item["effects"] = json.loads(item["effects"])
    return {"ingredients": data}


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


@app.get("/api/characters")
def list_characters(q: str = "") -> dict[str, Any]:
    with db() as conn:
        if q:
            data = rows(conn.execute("SELECT * FROM characters WHERE name LIKE ? ORDER BY name", (f"%{q}%",)))
        else:
            data = rows(conn.execute("SELECT * FROM characters ORDER BY name"))
    return {"characters": data}


@app.post("/api/characters")
def create_character(payload: CharacterCreate) -> dict[str, Any]:
    try:
        with db() as conn:
            cur = conn.execute("INSERT INTO characters(name) VALUES (?)", (payload.name.strip(),))
            char = dict(conn.execute("SELECT * FROM characters WHERE id=?", (cur.lastrowid,)).fetchone())
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
        data = rows(conn.execute(
            """
            SELECT i.name AS ingredient, e.name AS effect, cke.discovered_at
            FROM character_known_effects cke
            JOIN ingredients i ON i.id = cke.ingredient_id
            JOIN effects e ON e.id = cke.effect_id
            WHERE cke.character_id=?
            ORDER BY i.name, e.name
            """, (character_id,)
        ))
    return {"known_effects": data}


class CreatedRecipe(BaseModel):
    ingredient_names: list[str]
    effect_names: list[str]


@app.post("/api/characters/{character_id}/created-recipes")
def mark_created(character_id: int, payload: CreatedRecipe) -> dict[str, Any]:
    if len(payload.ingredient_names) not in (2, 3):
        raise HTTPException(400, "Recipe must have 2 or 3 ingredients")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM characters WHERE id=?", (character_id,)).fetchone():
            raise HTTPException(404, "Character not found")
        ingredient_ids = rows(conn.execute(
            f"SELECT id, name FROM ingredients WHERE name IN ({','.join('?' for _ in payload.ingredient_names)})",
            payload.ingredient_names,
        ))
        effect_ids = rows(conn.execute(
            f"SELECT id, name FROM effects WHERE name IN ({','.join('?' for _ in payload.effect_names)})",
            payload.effect_names,
        ))
        ingredient_by_name = {r["name"]: r["id"] for r in ingredient_ids}
        effect_by_name = {r["name"]: r["id"] for r in effect_ids}
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
                            (character_id, ingredient_by_name[ing_name], effect_by_name[eff_name]),
                        )
                        inserted += conn.total_changes
        conn.execute(
            "INSERT INTO created_recipes(character_id, ingredient_names, effect_names) VALUES (?, ?, ?)",
            (character_id, json.dumps(payload.ingredient_names), json.dumps(payload.effect_names)),
        )
    return {"ok": True, "marked": inserted}


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
