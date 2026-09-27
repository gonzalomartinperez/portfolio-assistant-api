"""ASGI compatibility entry point. Bootstrap owns dependency composition."""

from app.bootstrap.container import create_app

app = create_app()
