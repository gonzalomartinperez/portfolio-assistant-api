---
name: api-change-stream
description: "Change or investigate incremental provider streaming, LangGraph run lifecycle, cancellation, or the public HTTP/SSE contract. Use for stream and frontend-contract work, not corpus ranking or unrelated API business rules."
---

# Change streaming without losing the wire contract

Read [AGENTS.md](../../../AGENTS.md) unless already loaded. Obtain the failing or
requested event sequence, locale and run outcome. An investigation stays read-only
unless the user also requests a fix. Load [API/SSE behavior](../../../docs/api-contract.md)
and inspect [stream tests](../../../tests/test_workflow.py) before designing changes.

Trace [run policy](../../../app/application/runs.py) → [injected workflow](../../../app/ai/workflow.py)
→ [provider translation](../../../app/infrastructure/answer.py) →
[stream closure](../../../app/presentation/streaming.py) and [HTTP](../../../app/presentation/http.py).
Do not pass LangGraph state, SDK objects or HTTP requests into application contracts.

- Preserve `/api/v1/...`, named events, payloads, sequence/terminal semantics,
  session credentials, Origin/CSRF and explicit cancellation. Fifteen-second SSE
  comments have no sequence IDs. No hidden reasoning or internal tool payloads.
- A gated asynchronous provider must yield a first delta while completion is
  blocked. Slicing a finished answer is only fixture output, not live streaming.
- Exercise silent upstream cancellation, disconnect/send failure, timeout, partial
  output, provider/storage failure and shutdown as relevant. Close upstream work
  and resources. Partial text is not completed history; persistence precedes
  `message.completed`. Unknown usage retains reservations; never silently retry.

For authorized changes, use the maintained [verification commands](../../../docs/local-development.md#verification)
and relevant contract/workflow/real-service tests. Export with
`uv run python -m contracts.export`, then review artifact diffs against the baseline;
do not blindly regenerate away drift. Production-image and proxy smoke commands
are in the same guide and [runbook](../../../docs/deployment.md).

Publish a committed [frontend handoff](../../../docs/frontend-handoff.md) with an
immutable API SHA, artifact paths/examples and compatibility notes when changing
integration behavior. The frontend owner imports it; never edit their checkout.
Deliver event/lifecycle evidence and distinguish fixture from paid-provider results.
If support must break, propose versioning and request coordination before removal.
This workflow does not authorize paid calls, remote deployment or GitHub mutations.
