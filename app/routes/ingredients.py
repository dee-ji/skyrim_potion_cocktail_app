from __future__ import annotations

import json

from fastapi import APIRouter

from app.db import db, rows
from app.rarity import rarity_for_ingredient
from app.schemas import IngredientOut, IngredientsResponse

router = APIRouter(tags=["ingredients"])


@router.get("/api/ingredients", response_model=IngredientsResponse)
def ingredients() -> IngredientsResponse:
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
    return IngredientsResponse(
        ingredients=[IngredientOut.model_validate(item) for item in data]
    )
