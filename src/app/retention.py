"""Delegate the deprecated module invocation to the application package."""

from portfolio_assistant.bootstrap.entrypoints.retention import main
from portfolio_assistant.bootstrap.maintenance import prune

__all__ = ["main", "prune"]

if __name__ == "__main__":
    main()
