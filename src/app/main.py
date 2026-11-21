"""Expose the ASGI application at the deprecated uvicorn target."""

from portfolio_assistant.main import app

__all__ = ["app"]
