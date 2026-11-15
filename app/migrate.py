"""Deprecated `python -m app.migrate` shim; use `assistant-migrate` (app.bootstrap.entrypoints.migrate)."""

from app.bootstrap.migrations import main

if __name__ == "__main__":
    main()
