# Portfolio assistant API

Public FastAPI service for the public portfolio assistant. Fixture mode is the default. No paid model calls are enabled by this repository.

## Development

Use `uv sync --frozen`, `docker compose up -d`, `uv run python -m app.migrate`, and `uv run uvicorn app.main:app --reload`. See [local development](docs/local-development.md), [deployment](docs/deployment.md), and `IMPLEMENTATION_STATUS.md` for verification status.
