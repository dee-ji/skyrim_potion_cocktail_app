from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.config import DATA_PATH, get_db_path

POSITIVE_EFFECTS = {
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

NEGATIVE_EFFECTS = {
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


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rows(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cur.fetchall()]


def init_db() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
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
    ingredients = json.loads(Path(DATA_PATH).read_text(encoding="utf-8"))
    for item in ingredients:
        conn.execute(
            "INSERT OR IGNORE INTO ingredients(name, source) VALUES (?, ?)",
            (item["name"], item["source"]),
        )
        ingredient_id = conn.execute(
            "SELECT id FROM ingredients WHERE name=?", (item["name"],)
        ).fetchone()["id"]
        for idx, effect in enumerate(item["effects"], start=1):
            if effect in POSITIVE_EFFECTS:
                polarity = "positive"
            elif effect in NEGATIVE_EFFECTS:
                polarity = "negative"
            else:
                polarity = "mixed"
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
