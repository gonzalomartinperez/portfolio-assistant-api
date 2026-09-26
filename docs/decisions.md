# Decisions and sources · 2026-09-26

- Node 24 is LTS and matches the existing portfolio `.nvmrc`. Python 3.13 has five years of support but Python does not designate an LTS line. PostgreSQL 17 is supported through 2029. Neo4j 5.26 is an LTS line. See official [Node releases](https://nodejs.org/en/about/previous-releases), [Python PEP 602](https://peps.python.org/pep-0602/), [PostgreSQL versioning](https://www.postgresql.org/support/versioning/), and [Neo4j requirements](https://neo4j.com/docs/operations-manual/current/installation/requirements/).
- Fixture vectors use a deterministic 64-dimensional hash. [pgvector](https://github.com/pgvector/pgvector) supports exact scans and this small corpus does not justify an approximate index.
- [FastAPI SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/) supports POST streams. The public wire format is versioned independently of framework internals.
- The [OpenAI Responses streaming guide](https://developers.openai.com/api/docs/guides/streaming-responses) and [gpt-6-luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) were checked. The adapter remains opt-in with a simulated-client test. Account access and paid calls are unverified.
- Source code sync is explicit and confined to an allowlist of the public portfolio repository. A failed graph projection leaves the PostgreSQL active version unchanged.
