# Portfolio Assistant API

A bilingual assistant for exploring Gonzalo Martín Pérez's public professional
portfolio. It retrieves cited public evidence about projects, roles, technologies
and education, then streams an answer while keeping anonymous conversations
isolated. The [portfolio](https://github.com/gonzalomartinperez/portfolio) supplies
approved public content; the independently owned
native portfolio client consumes this API's committed contract; its rollout remains
disabled. The [backoffice](https://github.com/gonzalomartinperez/portfolio-assistant-backoffice)
is the independently owned authenticated administration surface. See the
[committed frontend handoff](docs/frontend-handoff.md).

**Current status:** working fixture-backed engineering release candidate on
`develop`. PostgreSQL/pgvector persistence, Neo4j relationship retrieval, LangGraph
orchestration, incremental provider streaming, sessions, security controls and
container checks are implemented. The default provider returns deterministic
source excerpts without paid credentials. Live-model quality, VPS capacity and
production deployment remain unverified. See [verification status](IMPLEMENTATION_STATUS.md).

## Run a free local demo

Use Linux/WSL, Docker Compose and **uv 0.13.0** from this repository root.
uv provisions the pinned Python 3.14.8; older uv download metadata may not support it:

```sh
uv sync --frozen
source scripts/fixture-env.sh
docker compose up --build -d --wait
uv run python -m app.migrate
uv run python -m app.knowledge_sync --source github --ref 1acbe54906c88398652aebb8eae0c217fd0d8821
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In another terminal run `uv run python -m scripts.demo` (or add `--locale es`).
No API key is needed. The fixture environment uses an isolated Compose project
and loopback database ports; see [local setup](docs/local-development.md) to avoid
port conflicts and run the full verification suite.

## How it works

A modular monolith separates `domain`, `application`, `ai`, `infrastructure`,
`presentation` and `bootstrap`. Application-owned ports isolate business policies
from FastAPI, LangGraph and database/provider SDKs. Architecture tests enforce the
direction; strict typing covers inner contracts and AI orchestration.

Exact vector search and bilingual lexical policies answer ordinary factual
questions. Bounded Neo4j paths add evidence for relationships such as projects and
roles sharing technologies. Provenance includes immutable source commits, chunks
and public line links. The [retrieval evaluation](docs/graph-retrieval.md) compares
vector, graph and hybrid strategies with real databases and fixture embeddings.
An authorized OpenAI adapter now supplies semantic embeddings; live quality still
requires evaluation. See [continuous knowledge synchronization](docs/knowledge-sync.md).

## Explore

- [Architecture and lifecycle](docs/architecture.md) · [decisions](docs/adrs/001-dependency-direction.md)
- [HTTP/SSE contract and examples](docs/api-contract.md) · [frontend handoff](docs/frontend-handoff.md)
- [Conversation behavior and before/after evaluation](docs/conversation-evaluation.md)
- [1000-question bilingual evaluation bank and safe harness](docs/assistant-evaluation.md)
- [Security/privacy and residual risks](docs/threat-model.md) · [private reporting](SECURITY.md)
- [Configuration](docs/environment.md) · [operations](docs/deployment.md) · [Coolify runtime handoff](docs/deployment-contract.md)
- [vps-ops dispatch request](docs/vps-ops-request.md) · [database image evidence](docs/verification/database-images-2026-10-10.md)
- [Shared VPS decision](docs/adrs/002-shared-kvm4-origin.md) · [CI jobs and release gates](docs/ci.md)
- [Contributing and Python conventions](CONTRIBUTING.md) · [release checklist](docs/release-checklist.md)

## Verify

```sh
uv run ruff check app tests contracts scripts
uv run ruff format --check app tests contracts scripts
uv run mypy
uv run pytest -q
```

The [full guide](docs/local-development.md#verification) adds real PostgreSQL/Neo4j,
contract drift, retrieval evaluation and production-container smoke tests. CI uses
locked dependencies, pinned actions/images and required checks on PRs into
`develop`. The intended deployment is a modest single VPS; resource measurements
are local observations, not capacity guarantees.

The assistant has no mutation tools, unrestricted browsing or private repository
access. Prompt instructions are not authorization controls, and fixture tests do
not prove live-model safety. Public visibility does not imply an open-source
license: no source license has been selected. See [third-party notices](THIRD_PARTY_NOTICES.md).

Recent verification: [authorized 244-turn OpenAI evaluation and fixes](docs/verification/live-depth-2026-10-10.md).
This records real generation, RAG/persistence audits and remaining release gates;
fixture evidence and live qualitative review are reported separately. Production
and the native portfolio assistant remain disabled.
