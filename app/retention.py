"""Deprecated `python -m app.retention` shim; use `assistant-retention` (app.bootstrap.entrypoints.retention)."""

from app.bootstrap.maintenance import prune

if __name__ == "__main__":
    print(prune())
