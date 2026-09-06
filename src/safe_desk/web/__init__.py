"""Local trader UI. No login, no secrets, dry-run default."""

from safe_desk.web.app import app, create_app

__all__ = ["app", "create_app"]
