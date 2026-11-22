# ADR030: RFC 9457 problem documents as an additive v1.1 error contract

Status: accepted (2026-11-22, master plan task M5-1; decision PAA-D17).

## Context and problem

Every public error was `{"code","message","request_id"}` with an English `message` derived from the code
(`code.replace("_", " ")`). Codes were free strings raised from several layers, framework 404 and 405
answers bypassed the envelope (`{"detail":"Not Found"}`), and clients had no machine-readable retry advice
or Spanish text. The [target state](../master-plan/target-state.md) (section 6) asks for RFC 9457 problem
documents with `code`, `retryable`, `retry_after_s` and EN and ES messages without breaking v1 consumers.
The portfolio site reads `response.json().code` and ignores the content type and other members.

## Decision drivers

- No v1 member, status code or documented media type is removed (`oasdiff breaking --fail-on WARN` stays green).
- A closed code vocabulary: no framework, provider or visitor text can reach an error body.
- Consumers can show a localized message and decide on retry without their own code table.
- Same mapping shape as pequeverso-assistant-api ADR-0013 (`urn:` type, `code` extension) for P6.

## Considered options

1. **A. Additive problem document.** Keep `code`, `message`, `request_id`; add `type`, `title`, `status`,
   `detail`, `instance`, `retryable`, `retry_after_s` and `messages` (`en`, `es`); serve
   `application/problem+json` to clients that ask for it; document both media types.
2. **B. Problem documents only under a new `/v2`.** No v1 change, but two error shapes to maintain and
   the site keeps localizing codes itself.
3. **C. Replace the v1 body.** Breaking; needs `contract-major` and coordinated consumer releases.

## Decision

Choose A. `src/portfolio_assistant/presentation/problems.py` owns the closed `ErrorCode` enum and the
catalog (status, title, English and neutral Latin American Spanish text, retry advice). Every error path
(application `RejectedError`, FastAPI and Starlette `HTTPException` including router 404 and 405,
request validation, the origin guard, the body-limit timeout and size guards, and the unexpected-fault
boundary) goes through `problems.response`. The body is the same for every client; the content type is
negotiated: `application/problem+json` when `Accept` contains it, otherwise the v1 `application/json`,
with `Vary: Accept`. The raised HTTP status is kept (catalog statuses match every raise site). An unknown code is mapped by status to a catalogued code, so
it can never be echoed. `type` is `urn:portfolio-assistant:error:<code>` and `instance` is
`urn:request:<request_id>`; neither needs hosting. `detail` and `message` carry the same English text.
`retry_after_s` is advice and is also sent as `Retry-After`; for `rate_limited` it is the length of the
hourly window (an upper bound), not the exact remaining time.

The OpenAPI component keeps its v1 name `ErrorBody` so generated consumer types stay stable. Every
documented 4xx and 5xx response keeps its `application/json` entry and gains `application/problem+json`
(`document_problem_media`). The public analytics route keeps the stale FastAPI `HTTPValidationError` JSON
entry for 422 until a contract phase, because changing it would be breaking for oasdiff; the actual body
is the problem document. `info.version` becomes `1.1.0`; the SSE `schema_version` stays `1` and
in-stream `run.failed` codes are out of scope for problem documents.

## Consequences

- Good: one source for status, retry advice and bilingual copy; the site can render `messages[locale]`.
- Good: v1 clients see the same status and content type as before, only with more members.
- Good: framework 404 and 405 and malformed bodies are now documented problem documents, which removes
  the Schemathesis malformed-body exception.
- Bad: two media types per error response in OpenAPI until the contract phase drops `application/json`
  (a later, labelled major change), and one stale 422 schema on the analytics route.
- Neutral: adding a code means one enum member and one catalog entry; tests fail otherwise.

## Confirmation

`tests/contract/test_problem_documents.py` checks that the catalog equals the enum, that every code raised
in `src` is catalogued (AST scan), bilingual completeness, that each document validates against the
committed `ErrorBody` schema, the 404, 405 (with `Allow`), 422, 403, 401 and 429 (`Retry-After`) wire
shapes, and that every documented error offers `application/problem+json`. `contracts/problem.examples.json`
(generated, one document per code) is validated in `tests/contract/test_schema_examples.py`. Schemathesis
and `scripts.contract_diff` run in the contract job.

## Amendment 2026-11-22: in-stream failures

The `run.failed` payload gains the optional members `retryable` and `messages` (`en`, `es`), always sent
by this server and filled from the same catalog plus three stream-only codes (`generation_failed`,
`provider_unavailable`, `budget_exhausted`); an unlisted code gets the `generation_failed` text. The
event stays a stream event, not a problem document. The SSE change is additive (no removed event or
required field), and the pinned site parser only requires `payload.code`.
`tests/contract/test_sse_conformance.py::test_run_failed_carries_retry_advice_and_bilingual_messages`
and `tests/resilience/test_dependency_failures.py` confirm it.
