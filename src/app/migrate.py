"""Delegate the deprecated module invocation to the application package."""

from portfolio_assistant.bootstrap.entrypoints.migrate import main

__all__ = ["main"]

if __name__ == "__main__":
    main()
