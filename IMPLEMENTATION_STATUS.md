# Implementation status · 2026-09-26

Both new repositories were bootstrapped private, then changed to public at the owner's explicit request. `main` contains only the one-time bootstrap. This task branch targets `develop` through a PR.

## Gates

- A · PASS locally: Python lockfile, offline OpenAPI and SSE schema, Compose and Dockerfile. Production image built.
- B · PASS locally: PostgreSQL sessions, ownership, CSRF, deletion, seven-day pruning, lease interruption and LangGraph Postgres checkpointer pass real integration. A separate development database restored from pg_dump with session, knowledge and checkpoint rows verified.
- C · PARTIAL: fixture HTTP → LangGraph/LangChain → pgvector and Neo4j → SSE terminal with citations passes real integration. Fixture text is deterministic source excerpts, not model quality.
- D · PASS locally: local and GitHub public-source adapters, allowlist, hashes, line provenance, Markdown sections and TS text fallback pass. Real two-commit sync reused 10 of 12 files; a second same-commit sync was a no-op. A simulated graph failure kept the prior PostgreSQL knowledge version active.
- E · PARTIAL: both localhost browser origins work. Mobile Spanish and isolated context ownership were exercised. Broader accessibility and error QA remain.
- F · PARTIAL: Origin, CSRF, rate, concurrency, idempotency, cancellation, lease interruption, retention and budget reservation/settlement pass local tests. A simulated Responses client passes; paid account and prompt-injection evaluation remain NOT RUN.
- G · IN PROGRESS: API and web images built; production API/web smoke reached 200 after startup. CI/PR integration and restore remain.
- H · DEFERRED: real OpenAI calls, VPS, DNS and main promotion require separate authorization.

## Evidence

`uv run pytest -q`: 4 passed, 4 integration tests skipped without `TEST_INTEGRATION=1`. `TEST_INTEGRATION=1 uv run pytest -q tests/test_integration.py`: 4 passed against local PostgreSQL and Neo4j. `uv run ruff check app tests contracts`: pass. Browser checks used Chromium at localhost ports 3000 and 3001, English and Spanish, mobile 390×844, two isolated contexts; cross-session read returned 404. No physical devices tested. Steady resource measurements and restore are pending.
