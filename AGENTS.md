# Agent rules

Use English for code, documentation and commits. Keep fixture mode default. Never read, log, commit or use a real API key without explicit authorization. Only approved public portfolio content may enter the runtime corpus. Integrate task branches through PRs into develop. Promote develop to main only with explicit owner authorization, passing Quality checks and satisfied review requirements. Main promotion does not authorize deployment.

## Architecture and verification

`app/domain` is pure standard-library policy. `app/application` owns use cases and
ports and may import domain. Neither imports outer layers. `app/ai` implements
workflow/retrieval with injected capabilities, never concrete I/O. Infrastructure
implements persistence/provider/source ports; presentation handles HTTP/SSE;
bootstrap composes clients and lifespan. Preserve v1 wire artifacts.

Run `uv sync --frozen`, `uv run ruff check app tests contracts scripts`,
`uv run ruff format --check app tests contracts scripts`, `uv run mypy`, and
`uv run pytest -q`. Real integration requires migrations and the pinned approved
public corpus, then `TEST_INTEGRATION=1 uv run pytest -q`. Export contracts with
`uv run python -m contracts.export`; inspect drift before committing.
Use isolated Compose projects, ports and databases. Do not stop shared services
or delete volumes. Document fixture versus live verification separately.
