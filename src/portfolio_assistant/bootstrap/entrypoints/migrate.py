"""``assistant-migrate``: apply application migrations (one-shot pre-deploy job)."""


def main() -> None:
    """Apply application migrations like ``python -m app.migrate``."""
    from portfolio_assistant.bootstrap.migrations import main as run

    run()
