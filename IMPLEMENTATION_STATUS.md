# Implementation status · 2026-09-26

Both new repositories were bootstrapped private, then changed to public at the owner's explicit request. `main` contains only the one-time bootstrap. This task branch targets `develop` through a PR.

## Gates

- A · PASS locally: Python lockfile, offline OpenAPI and SSE schema, Compose and Dockerfile. Production image built.
- B · PARTIAL: PostgreSQL sessions, ownership, CSRF, deletion and LangGraph Postgres checkpointer pass real integration. Lease recovery and backup restore still need verification.
- C · PARTIAL: fixture HTTP → LangGraph/LangChain → pgvector and Neo4j → SSE terminal with citations passes real integration. Fixture text is deterministic source excerpts, not model quality.
- D · PARTIAL: local and GitHub public-source adapters, allowlist, hashes, provenance and same-commit no-op pass. Cross-commit incremental reuse and rollback test remain.
- E · PARTIAL: both localhost browser origins work. Mobile Spanish and isolated context ownership were exercised. Broader accessibility and error QA remain.
- F · PARTIAL: Origin, CSRF, per-session rate and global concurrency checks exist; paid ledger reservation exists but is not connected to a real provider. Restart, prompt-injection and budget tests remain.
- G · IN PROGRESS: API and web images built; production API/web smoke reached 200 after startup. CI/PR integration and restore remain.
- H · DEFERRED: real OpenAI calls, VPS, DNS and main promotion require separate authorization.

## Evidence

`uv run pytest -q`: 4 passed, 2 integration tests skipped without `TEST_INTEGRATION=1`. `TEST_INTEGRATION=1 uv run pytest -q tests/test_integration.py`: 2 passed against local PostgreSQL and Neo4j. `uv run ruff check app tests contracts`: pass. Browser checks used Chromium at localhost ports 3000 and 3001, English and Spanish, mobile 390×844, two isolated contexts; cross-session read returned 404. No physical devices tested. Steady resource measurements and restore are pending.
