"""ASGI module served by `assistant-api` (uvicorn `app.main:app`). Bootstrap owns dependency composition."""

from app.bootstrap.container import create_app

app = create_app()
