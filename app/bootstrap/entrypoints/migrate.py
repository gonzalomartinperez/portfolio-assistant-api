"""``assistant-migrate``: apply application migrations (one-shot pre-deploy job)."""


def main() -> None:
    """Apply application migrations like ``python -m app.migrate``."""
    from app.bootstrap.migrations import main as run

    run()
