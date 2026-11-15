"""Deprecated `python -m app.migrate` shim; use `assistant-migrate` (app.bootstrap.entrypoints.migrate)."""

from app.bootstrap.entrypoints.migrate import main

if __name__ == "__main__":
    main()
