# Deterministic local demo

Prerequisites: WSL/Linux filesystem, Git, Docker Compose, uv and Python 3.14
(`uv` installs the pinned interpreter when needed). No model key is needed.
All commands run from this repository root. The frontend is independently owned;
these instructions do not modify its checkout or services.

```sh
uv sync --frozen
source scripts/fixture-env.sh
docker compose up -d --wait
uv run python -m app.migrate
uv run python -m app.knowledge_sync --source github --ref 1acbe54906c88398652aebb8eae0c217fd0d8821
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

The fixture script uses project `assistant-fixture` and loopback ports
55433 (PostgreSQL), 57688 (Bolt), 57475 (Neo4j HTTP). Override `ASSISTANT_PROJECT`,
`POSTGRES_PORT`, `NEO4J_PORT`, `NEO4J_HTTP_PORT` **before** sourcing it if occupied.
Each project gets separate volumes. Never stop another project's services or run
`down -v`. `docker compose stop` stops only the selected project and preserves data.
The CLI's GitHub source fetches the exact approved public revision above; a local
approved checkout can use `--repo ../portfolio --ref <full SHA>` instead.

`GET http://localhost:8000/health/live` is dependency-free. `/health/ready` requires
migrations, an active public corpus and graph connectivity. Browser origins
`http://localhost:3000` and `http://localhost:3001` are trusted by default. Use
`localhost` consistently for browser cookies. See [API examples](api-contract.md).

For a terminal demo while the server runs:

```sh
uv run python -m scripts.demo
```

The demo creates a session, streams a bilingual public question, prints public
answer text and deletes its session. It does not print credentials.

## Verification

```sh
uv run ruff check app tests contracts scripts
uv run ruff format --check app tests contracts scripts
uv run mypy
uv run pytest -q                         # Pure/contract tests; real-service tests skip.
TEST_INTEGRATION=1 uv run pytest -q      # Uses the isolated fixture databases above.
uv run python -m contracts.export
git diff --exit-code contracts/openapi.json contracts/sse.schema.json
uv run python -m scripts.evaluate_retrieval
uv run python -m scripts.benchmark_fixture
uv run python -m scripts.scan_secrets
docker build -t portfolio-assistant-api:fixture .
uv run python -m scripts.container_smoke --image portfolio-assistant-api:fixture
```

Real-service tests create and delete their own anonymous sessions and temporary
index versions. The indexing test restores the original active version. Run them
only against an isolated test corpus, never production. Container smoke uses Linux
host networking and a dedicated loopback API port; it removes only its own
containers. Fixture timing is local evidence, not a production capacity guarantee.

## Dependencies and maintenance

`uv.lock` and image digests pin reproducible installs. Python 3.14 is checked in the frozen lockfile, tests and production image. Mypy is the only new development dependency in this migration; it checks
inner contracts and AI orchestration strictly. No ORM/queue/new service was added.
Run `uv run python -m app.retention` every minute to prune expired data and retry
checkpoint tombstones. Detailed backup, upgrade and shutdown procedures are in
[operations](deployment.md). Configuration is documented in [environment](environment.md).
