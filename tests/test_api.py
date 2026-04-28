from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.app_factory import create_app


def create_character(client: TestClient, name: str = "Dragonborn") -> int:
    response = client.post("/api/characters", json={"name": name})
    assert response.status_code == 200
    return response.json()["character"]["id"]


def test_ingredients_endpoint_returns_seeded_data(monkeypatch, tmp_path):
    monkeypatch.setenv("SKYRIM_ALCHEMY_DB", str(tmp_path / "test.db"))
    with TestClient(create_app()) as client:
        response = client.get("/api/ingredients")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ingredients"]
    aloe = next(
        item for item in payload["ingredients"] if item["name"] == "Aloe Vera Leaves"
    )
    assert aloe["source"] == "_ResourcePack.esl"
    assert len(aloe["effects"]) == 4


def test_inventory_set_and_adjust(monkeypatch, tmp_path):
    monkeypatch.setenv("SKYRIM_ALCHEMY_DB", str(tmp_path / "test.db"))
    with TestClient(create_app()) as client:
        character_id = create_character(client)
        response = client.put(
            f"/api/characters/{character_id}/inventory",
            json={"ingredient_name": "Blue Mountain Flower", "quantity": 3},
        )
        assert response.status_code == 200
        assert response.json()["item"]["quantity"] == 3

        response = client.post(
            f"/api/characters/{character_id}/inventory/adjust",
            json={"ingredient_name": "Blue Mountain Flower", "delta": -2},
        )
        assert response.status_code == 200
        assert response.json()["item"]["quantity"] == 1

        response = client.get(f"/api/characters/{character_id}/inventory")
        assert response.status_code == 200
        assert response.json()["inventory"][0]["name"] == "Blue Mountain Flower"
        assert response.json()["inventory"][0]["quantity"] == 1


def test_known_effects_add_and_remove(monkeypatch, tmp_path):
    monkeypatch.setenv("SKYRIM_ALCHEMY_DB", str(tmp_path / "test.db"))
    with TestClient(create_app()) as client:
        character_id = create_character(client)

        response = client.post(
            f"/api/characters/{character_id}/known-effects",
            json={
                "ingredient_name": "Blue Mountain Flower",
                "effect_names": ["Restore Health", "Fortify Conjuration"],
            },
        )
        assert response.status_code == 200
        assert response.json()["marked"] == 2

        response = client.get(f"/api/characters/{character_id}/known-effects")
        assert response.status_code == 200
        known_effects = response.json()["known_effects"]
        assert len(known_effects) == 2

        response = client.request(
            "DELETE",
            f"/api/characters/{character_id}/known-effects",
            json={
                "ingredient_name": "Blue Mountain Flower",
                "effect_names": ["Restore Health"],
            },
        )
        assert response.status_code == 200
        assert response.json()["removed"] == 1


def test_created_recipe_consumes_inventory_and_marks_known(monkeypatch, tmp_path):
    monkeypatch.setenv("SKYRIM_ALCHEMY_DB", str(tmp_path / "test.db"))
    with TestClient(create_app()) as client:
        character_id = create_character(client)

        client.put(
            f"/api/characters/{character_id}/inventory",
            json={"ingredient_name": "Blue Mountain Flower", "quantity": 1},
        )
        client.put(
            f"/api/characters/{character_id}/inventory",
            json={"ingredient_name": "Wheat", "quantity": 1},
        )

        response = client.post(
            f"/api/characters/{character_id}/created-recipes",
            json={
                "ingredient_names": ["Blue Mountain Flower", "Wheat"],
                "effect_names": ["Restore Health", "Fortify Health"],
            },
        )
        assert response.status_code == 200
        inventory_rows = {
            item["name"]: item["quantity"] for item in response.json()["inventory"]
        }
        assert inventory_rows["Blue Mountain Flower"] == 0
        assert inventory_rows["Wheat"] == 0

        response = client.get(f"/api/characters/{character_id}/known-effects")
        known_effects = {
            (row["ingredient"], row["effect"])
            for row in response.json()["known_effects"]
        }
        assert ("Blue Mountain Flower", "Restore Health") in known_effects
        assert ("Wheat", "Restore Health") in known_effects


def test_created_recipe_rejects_missing_inventory(monkeypatch, tmp_path):
    monkeypatch.setenv("SKYRIM_ALCHEMY_DB", str(tmp_path / "test.db"))
    with TestClient(create_app()) as client:
        character_id = create_character(client)
        response = client.post(
            f"/api/characters/{character_id}/created-recipes",
            json={
                "ingredient_names": ["Blue Mountain Flower", "Wheat"],
                "effect_names": ["Restore Health"],
            },
        )
        assert response.status_code == 400
        assert "Not enough inventory" in response.text
