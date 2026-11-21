"""ASGI module served by `assistant-api` (uvicorn `portfolio_assistant.main:app`). Bootstrap owns dependency composition."""

from portfolio_assistant.bootstrap.container import create_app

app = create_app()
