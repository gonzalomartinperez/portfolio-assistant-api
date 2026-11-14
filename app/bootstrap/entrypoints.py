"""Console-script entry points; the `python -m` forms remain supported."""


def api() -> None:
    """Run the API with the same settings as the container command."""
    import uvicorn

    uvicorn.run(
        'app.main:app',
        host='0.0.0.0',
        port=8000,
        access_log=False,
        proxy_headers=False,
        timeout_graceful_shutdown=15,
    )


def migrate() -> None:
    """Apply application migrations like `python -m app.migrate`."""
    from app.bootstrap.migrations import main

    main()


def retention() -> None:
    """Prune expired data like `python -m app.retention`."""
    from app.bootstrap.maintenance import prune

    print(prune())


def knowledge_sync() -> None:
    """Index the approved public corpus like `python -m app.knowledge_sync`."""
    from app.bootstrap.indexing import main

    main()


def knowledge_watch() -> None:
    """Run the knowledge watcher like `python -m app.knowledge_watch`."""
    import asyncio

    from app.bootstrap.knowledge_watch import run

    asyncio.run(run())
