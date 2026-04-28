from __future__ import annotations

try:
    from app.app_factory import app, create_app
except ModuleNotFoundError:
    from app_factory import app, create_app

__all__ = ["app", "create_app"]
