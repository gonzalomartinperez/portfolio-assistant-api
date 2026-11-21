---
name: api-change-stream
description: "Changes or investigates incremental provider streaming, the LangGraph run lifecycle, cancellation and SSE behavior. Use when a task touches how a run streams, cancels or terminates. Not for adding or changing contract fields and artifacts (use refresh-contract), corpus ranking (use api-maintain-knowledge) or application business rules (use api-change-use-case)."
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# Change streaming without losing the wire contract

Read [AGENTS.md](../../../AGENTS.md) unless already loaded. Obtain the failing or
requested event sequence, locale and run outcome. An investigation stays read-only
unless the user also requests a fix. Load [API/SSE behavior](../../../docs/reference/api-contract.md)
and inspect [stream tests](../../../tests/unit/test_workflow.py) before designing changes.

Trace [run policy](../../../src/portfolio_assistant/application/runs.py) → [injected workflow](../../../src/portfolio_assistant/ai/workflow.py)
→ [provider translation](../../../src/portfolio_assistant/adapters/providers/answer.py) →
[stream closure](../../../src/portfolio_assistant/presentation/streaming.py) and [HTTP](../../../src/portfolio_assistant/presentation/http.py).
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

For authorized changes, use the maintained [verification commands](../../../docs/tutorials/local-development.md#verification)
and relevant contract/workflow/real-service tests. Export with
`uv run python -m contracts.export`, then review artifact diffs against the baseline;
do not blindly regenerate away drift. Production-image and proxy smoke commands
are in the same guide and [runbook](../../../docs/how-to/deploy-with-vps-ops.md).

Publish a committed [frontend handoff](../../../docs/reference/frontend-handoff.md) with an
immutable API SHA, artifact paths/examples and compatibility notes when changing
integration behavior. The frontend owner imports it; never edit their checkout.
Deliver event/lifecycle evidence and distinguish fixture from paid-provider results.
If support must break, propose versioning and request coordination before removal.
This workflow does not authorize paid calls, remote deployment or GitHub mutations.
