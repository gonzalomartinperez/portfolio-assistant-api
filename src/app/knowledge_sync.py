"""Delegate the deprecated module invocation to the application package."""

from portfolio_assistant.bootstrap.entrypoints.knowledge_sync import main
from portfolio_assistant.bootstrap.indexing import sync

__all__ = ["main", "sync"]

if __name__ == "__main__":
    main()
