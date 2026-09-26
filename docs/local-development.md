# Local fixture setup

Source and Git worktrees live under `~/projects/github/gonzalomartinperez/`. Node 24 LTS, Python 3.13, uv and Docker Compose are required. Fixture mode never calls OpenAI even if an API key exists on the machine.

```sh
cd ~/projects/github/gonzalomartinperez/portfolio-assistant-api
docker compose up -d
uv sync --frozen
uv run python -m app.migrate
uv run python -m app.knowledge_sync --repo ../portfolio --ref origin/develop
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal run `cd ~/projects/github/gonzalomartinperez/portfolio-assistant-web && nvm use && npm ci && npm run dev`. Open `http://localhost:3001`. To preview the native panel, use the portfolio task worktree or merged `develop`, `nvm use && npm ci && npm run dev -- --webpack --port 3000`, then open `http://localhost:3000` and choose **Ask AI**. Both frontends call the API directly. The dev session cookie is for `localhost`; use the same hostname on all three ports.

Public source sync is explicit. `uv run python -m app.knowledge_sync --source github` fetches only `gonzalomartinperez/portfolio` from GitHub and activates a new version after both projections finish. Running the same commit again returns `changed: false`; across commits, unchanged blobs reuse stored chunks and embeddings. The CLI reports `embedded_chunks` and `reused_files`. No chat request triggers sync. Use `uv run python -m app.retention` on a daily schedule to purge expired anonymous sessions and LangGraph checkpoints. Never use `docker compose down -v` in routine development.

## Verification

```sh
uv run ruff check app tests contracts
uv run pytest -q
TEST_INTEGRATION=1 uv run pytest -q tests/test_integration.py
uv run python -m contracts.export && git diff --exit-code contracts/openapi.json
docker build -t portfolio-assistant-api:fixture .
```

The web uses `npm test && npm run build && docker build -t portfolio-assistant-web:fixture .`. The portfolio uses its `npm run check` gate. Browser checks require API, both databases and both web servers running.

## Local backup and restore

PostgreSQL contains sessions, history, checkpoints and active version. Create a private backup with `docker compose exec -T postgres pg_dump -U assistant -Fc assistant > /path/with/restricted/permissions/assistant.dump`. Restore only to a separate development database with `pg_restore --clean --if-exists`; never overwrite the current database during a smoke test. Neo4j is a rebuildable projection from the approved public source. For future production backups, Neo4j Community needs an offline database dump; see the deployment guide.
