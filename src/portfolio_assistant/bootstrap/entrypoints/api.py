"""``assistant-api``: serve the ASGI app with the container's uvicorn settings."""


def main() -> None:
    """Run the API with the same settings as the image command."""
    import uvicorn

    uvicorn.run(
        "portfolio_assistant.main:app",
        host="0.0.0.0",
        port=8000,
        access_log=False,
        proxy_headers=False,
        timeout_graceful_shutdown=15,
    )
