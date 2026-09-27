# Bounded release-candidate acceptance

Scope: fixture-backed public engineering release on `develop`. No production
promotion, paid model calls or frontend edits. Stop when these gates pass; further
visual/style changes do not extend the task.

| Priority | Acceptance | Evidence |
| --- | --- | --- |
| Correctness | Complete session → retrieval → incremental answer → citations → persistence journey; unchanged v1 semantics | Real-service integration and event-schema tests |
| Correctness | Silent provider cancellation, disconnect, partial output, timeout, storage failure and shutdown release resources | Gated async provider, ASGI and production smoke tests |
| Security | Ownership, CSRF, origins/cookies, byte/history/concurrency/rate/cost bounds enforced outside model | Security and transaction tests |
| Security | Public source allowlist, blob/mode limits, fixed remote, bounded graph queries, redacted errors/logs | Ingest tests, threat model, redacted history scan |
| Integration | Deterministic committed OpenAPI/SSE and immutable frontend handoff | Artifact drift check and handoff document |
| Knowledge | Bilingual direct/relationship/multi-hop/ambiguous/no-answer evaluation; failed index preserves active corpus | Real pgvector/Neo4j evaluation and recovery tests |
| Maintainability | Six layers, import direction, no SQL in HTTP/application, typed inner and AI contracts | Architecture tests, strict mypy |
| Maintainability | Reproducible migrations, checksum/order checks, safe cleanup and local transactions | Migration and checkpoint tests |
| Presentation | README demo works from clean checkout; focused guides; Google-derived conventions and verified security channel | Clean-checkout run and documentation audit |
| Integration | Required CI, non-root container, health/SSE/shutdown smoke; PR-only integration | GitHub checks and smoke artifacts |

## Final audit boundaries

Live model quality/injection testing, real embeddings, TLS/reverse-proxy/browser
integration, VPS load, encrypted off-site restore and production operations need
separate authorized verification. There is no chosen source license. These must
remain visible rather than being described as completed release gates.
