from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "ingredients.json"
STATIC_DIR = BASE_DIR / "static"


def get_db_path() -> Path:
    return Path(os.environ.get("SKYRIM_ALCHEMY_DB", BASE_DIR / "skyrim_alchemy.db"))
