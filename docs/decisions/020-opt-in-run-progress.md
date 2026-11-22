# ADR020: Opt-in `run.progress` events derived in the presentation layer

Status: accepted (2026-11-22, master plan task M5-2; decision PAA-D17).

## Context and problem

Between `run.started` and the first answer text a visitor sees no change, although the run is retrieving
evidence and then generating. The [target state](../master-plan/target-state.md) (section 6) adds a
`run.progress` event with `phase` in `retrieving`, `reading`, `writing`, sent only on request so strict v1
consumers see no new event. The current portfolio site parser (`src/features/assistant/adapters/sse.ts`
at `3785df8`) throws on any event type outside the v1 set, so a default-on event would break it.

## Decision drivers

- v1 streams stay byte-compatible: same events, same contiguous sequence numbers.
- No internal state, tool names, timings or graph nodes in public progress (api-contract "Stream order").
- No change to the run lifecycle, cancellation timing or persisted state.
- Proof against the real consumer code, not only our schema.

## Considered options

1. **A. Derive phases in presentation from the v1 events, opt-in by header.** `retrieving` after
   `run.started`, `reading` after `run.status`, `writing` before the first `message.delta` or
   `message.completed`.
2. **B. Emit phases from `RunService` and filter them in presentation.** Closer to the work, but it changes
   the application event sequence that 13 lifecycle and cancellation tests pin, for no extra information.
3. **C. Default-on event.** Breaks the current site parser.

## Decision

Choose A. `presentation/progress.py` (`ProgressPhases.expand`) inserts the phases only when the stream
request carries `X-Assistant-Progress: 1` (OpenAPI header parameter, values `0` and `1`; CORS allows the
header). The SSE schema gains the `run.progress` event with a closed payload. The phases mark milestones
the run already reports, so they never claim work that did not happen, and they never follow a terminal.
Turning the event on by default needs the site parser to tolerate it first (portfolio lead handoff) and a
later decision.

## Consequences

- Good: no application or lifecycle change; v1 clients are unaffected by construction.
- Good: the cross-repo `site-stream` job runs the site's own parser on the committed examples.
- Bad: `reading` and `writing` are coarse; finer progress would need workflow events (PAA-M5-X scope).
- Neutral: `sse.schema.json` lists the event, so schema-driven consumers learn it exists before using it.

## Confirmation

`tests/contract/test_sse_conformance.py` checks that v1 streams never carry `run.progress`, that the
opted-in order and contiguous sequences hold, that the terminal stays last, and that the payload is closed.
`tests/integration/test_integration.py` checks the header end to end and the CORS preflight.
`tests/contract/test_schema_examples.py` validates the `opt_in_progress` example.
`.github/workflows/cross-repo.yml` job `site-stream` runs `scripts/site_stream_compat.mjs` against the
pinned site.
