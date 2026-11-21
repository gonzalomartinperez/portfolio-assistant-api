"""``assistant-knowledge-watch``: run the long-lived knowledge watcher."""


def main() -> None:
    """Run the knowledge watcher like ``python -m app.knowledge_watch``."""
    import asyncio

    from portfolio_assistant.bootstrap.knowledge_watch import run

    asyncio.run(run())
