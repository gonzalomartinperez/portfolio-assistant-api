"""Delegate the deprecated module invocation to the application package."""

from portfolio_assistant.bootstrap.entrypoints.knowledge_watch import main
from portfolio_assistant.bootstrap.knowledge_watch import run

__all__ = ["main", "run"]

if __name__ == "__main__":
    main()
