"""Deprecated `python -m app.retention` shim; use `assistant-retention` (app.bootstrap.entrypoints.retention)."""

from app.bootstrap.entrypoints.retention import main
from app.bootstrap.maintenance import prune

__all__ = ["main", "prune"]

if __name__ == "__main__":
    main()
