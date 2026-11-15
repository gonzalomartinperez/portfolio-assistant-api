"""Deprecated `python -m app.knowledge_watch` shim; use `assistant-knowledge-watch` (app.bootstrap.entrypoints.knowledge_watch)."""

from app.bootstrap.entrypoints.knowledge_watch import main
from app.bootstrap.knowledge_watch import run

__all__ = ["main", "run"]

if __name__ == "__main__":
    main()
