"""Deprecated `python -m app.knowledge_watch` shim; use `assistant-knowledge-watch` (app.bootstrap.entrypoints.knowledge_watch)."""

import asyncio

from app.bootstrap.knowledge_watch import run

__all__ = ["run"]

if __name__ == "__main__":
    asyncio.run(run())
