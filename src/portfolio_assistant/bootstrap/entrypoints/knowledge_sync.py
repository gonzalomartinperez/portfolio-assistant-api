"""``assistant-knowledge-sync``: index an approved public corpus revision."""


def main() -> None:
    """Index the approved public corpus like ``python -m app.knowledge_sync``."""
    from portfolio_assistant.bootstrap.indexing import main as run

    run()
