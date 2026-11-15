"""Deprecated `python -m app.knowledge_sync` shim; use `assistant-knowledge-sync` (app.bootstrap.entrypoints.knowledge_sync)."""

from app.bootstrap.indexing import main, sync

__all__ = ["main", "sync"]

if __name__ == "__main__":
    main()
