# Rubric: senior designer — API and streaming UX (v1)

Focus from the research: the UX surfaces the API exposes: the SSE streaming contract,
error states, messages and their localization, and perceived progress. The visual
frontend belongs to other repositories and is out of scope; this lens judges what the
API makes possible or impossible for a good experience.

Total 100 points. Point allocation is the v1 proposal (see [rules](README.md)).

| # | Criterion | Max | 95+ looks like | Baseline evidence (2026-10-24) |
|---|---|---|---|---|
| 1 | Stream contract honesty | 20 | ordered `sequence`, `schema_version`, exactly one explicit terminal (`run.completed`, `run.failed`, `run.cancelled`); a broken connection is never shown as completion; mid-stream cancellation tested end to end | strong: 7 events with sequence, schema version and explicit terminals |
| 2 | Perceived progress | 20 | `run.status` phases cover the wait (`understanding`, `retrieving`, `evidence_found`, `writing`) so a client can say "Searching projects…"; heartbeat keeps the connection visibly alive | weak: only `evidence_found` during 1–3 s of retrieval + TTFT |
| 3 | Error states a client can design for | 20 | `code` is an enum in OpenAPI and SSE; `retryable` and `retry_after_s` present; RFC 9457-style `type`; every code has a designed client state | weak: free-string `FailedPayload.code`, no retry hints, not RFC 9457 |
| 4 | Human messages and localization | 15 | reviewed EN (natural US English) and ES (neutral Latin American Spanish) message per code, actionable and calm | weak: default message is `code.replace('_', ' ')` ("rate limited") |
| 5 | Interruption and recovery | 15 | partial output preserved and labelled; recovery checks saved history; limits and unavailability have distinct, safe states | partly present (README gallery shows interruption and unavailable states) |
| 6 | Contract evolution | 10 | changes are additive within v1 (v1.1), checked by oasdiff/JSON Schema diff; breaking changes require `contract-major` + ADR | v1 frozen artifacts exist; no automated breaking-change check |

Acceptance for P5 (from the research): the designer validates EN/ES error messages and
progress phases.

Evidence to collect per review: the SSE schema and OpenAPI on the reviewed commit, a
recorded fixture stream per terminal state, and the EN/ES message table.
