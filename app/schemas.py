from __future__ import annotations

from pydantic import BaseModel, Field


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class CharacterOut(BaseModel):
    id: int
    name: str
    created_at: str


class CharactersResponse(BaseModel):
    characters: list[CharacterOut]


class CharacterResponse(BaseModel):
    character: CharacterOut


class IngredientOut(BaseModel):
    id: int
    name: str
    source: str
    effects: list[str]
    rarity: str
    rarity_label: str
    rarity_rank: int
    rarity_note: str


class IngredientsResponse(BaseModel):
    ingredients: list[IngredientOut]


class InventoryItemOut(BaseModel):
    name: str
    source: str
    quantity: int
    rarity: str
    rarity_label: str
    rarity_rank: int
    rarity_note: str


class InventoryResponse(BaseModel):
    inventory: list[InventoryItemOut]


class InventoryUpdate(BaseModel):
    ingredient_name: str = Field(min_length=1)
    quantity: int = Field(ge=0)


class InventoryAdjust(BaseModel):
    ingredient_name: str = Field(min_length=1)
    delta: int


class InventoryMutationResponse(BaseModel):
    ok: bool = True
    item: InventoryItemOut


class KnownEffectOut(BaseModel):
    ingredient: str
    effect: str
    discovered_at: str


class KnownEffectsResponse(BaseModel):
    known_effects: list[KnownEffectOut]


class KnownEffectsUpdate(BaseModel):
    ingredient_name: str = Field(min_length=1)
    effect_names: list[str] = Field(min_length=1)


class KnownEffectsMutationResponse(BaseModel):
    ok: bool = True
    marked: int | None = None
    removed: int | None = None


class CreatedRecipe(BaseModel):
    ingredient_names: list[str]
    effect_names: list[str]
    consume_inventory: bool = True


class RecipeInventoryItemOut(BaseModel):
    name: str
    quantity: int


class CreatedRecipeResponse(BaseModel):
    ok: bool = True
    marked: int
    inventory: list[RecipeInventoryItemOut]


class OkResponse(BaseModel):
    ok: bool = True
