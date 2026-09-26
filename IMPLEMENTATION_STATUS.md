# Implementation status · 2026-09-26

Both new repositories were bootstrapped private, then changed to public at the owner's explicit request. `main` contains only the one-time bootstrap. Feature PRs #1 and #2 are merged into `develop`; the paired web PR #1 and portfolio PR #72 are also merged into their `develop` branches.

## Gates

- A · PASS locally: Python lockfile, offline OpenAPI and SSE schema, Compose and Dockerfile. Production image built.
- B · PASS locally: PostgreSQL sessions, ownership, CSRF, deletion, seven-day pruning, lease interruption and LangGraph Postgres checkpointer pass real integration. A separate development database restored from pg_dump with session, knowledge and checkpoint rows verified.
- C · PARTIAL: fixture HTTP → LangGraph/LangChain → pgvector and Neo4j → SSE terminal with citations passes real integration. Fixture text is deterministic source excerpts, not model quality.
- D · PASS locally: local and GitHub public-source adapters, allowlist, hashes, line provenance, Markdown sections and TS text fallback pass. Real two-commit sync reused 10 of 12 files; a second same-commit sync was a no-op. A simulated graph failure kept the prior PostgreSQL knowledge version active.
- E · PASS locally: both localhost browser origins work. Native English and Spanish panel tests passed on desktop and mobile, including focus return and API-unavailable behavior. Isolated context ownership was exercised. A full cross-browser accessibility audit remains NOT RUN.
- F · PARTIAL: Origin, CSRF, rate, concurrency, idempotency, cancellation, lease interruption, retention and budget reservation/settlement pass local tests. A simulated Responses client passes; paid account and prompt-injection evaluation remain NOT RUN.
- G · PASS locally: API and web images built; production API/web smoke reached 200 after startup. A PostgreSQL development backup restored into a separate database, including sessions, knowledge versions and checkpoints. The final public portfolio `develop` commit was synced into 74 cited chunks from 12 allowlisted files. Idle containers used about 874 MiB combined before the OS, proxy or Coolify. Representative VPS load testing remains NOT RUN.
- H · DEFERRED: real OpenAI calls, VPS, DNS and main promotion require separate authorization.

## Evidence

`TEST_INTEGRATION=1 uv run pytest -q`: 8 passed against local PostgreSQL and Neo4j. `uv run ruff check app tests contracts`: pass. Browser checks used Chromium at localhost ports 3000 and 3001, English and Spanish, mobile 390×844, two isolated contexts; cross-session read returned 404. No physical devices tested. The paid-model smoke test, full cross-browser accessibility audit and representative VPS load test remain NOT RUN.
