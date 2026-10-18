# Manual synthetic evaluation export

This optional operator command sends **one aggregate synthetic-evaluation run** to
LangSmith. It is not visitor tracing, an automatic judge, a dashboard integration or
an alternative to the local evaluation report. No account, external export, retention
policy or paid LangSmith plan was activated during implementation.

The public API never constructs this exporter. Global `LANGSMITH_TRACING` and
`LANGCHAIN_TRACING*` remain rejected by application settings. Private first-party
OpenTelemetry is a separate default-off mechanism; see [observability](private-observability.md).

## Offline validation

Create an operator-owned JSON file containing exactly these fields:

```json
{
  "scope": "synthetic_evaluation",
  "source_commit": "02b6f2784564669597fe8a4c2adf53bf807737a6",
  "cases": 6,
  "completed": 6,
  "failed": 0,
  "total_ms": 33676
}
```

The SHA above identifies a real source revision; the counts/time are example input,
not a claim of evaluation results. `source_commit` requires 40 lowercase hexadecimal
characters. Counts must be integers, 1–10,000 cases, with completed + failed = cases;
total time is an integer from 0 through 3,600,000 milliseconds. Unknown fields and
files larger than 2,048 bytes are rejected. This declaration does not prove that an
operator used synthetic data: do not derive it from visitor/session records.

```bash
uv run python -m app.bootstrap.evaluation_export path/to/summary.json
uv run pytest -q tests/test_evaluation_export.py tests/test_architecture.py
```

The first command returns `{"status": "disabled"}`. It constructs no SDK client and
makes no network request, even when unrelated LangSmith credentials exist. It does
not generate model responses, read conversation tables or consume OpenAI credits.
Never pass an existing raw answer report: it intentionally fails the closed schema.

## Separately authorized export

Before external use, approve the destination account/project, access controls,
retention and potential service charges. This document and a source merge provide
no such authorization. Deliver an evaluation-scoped key only to the manual operator
process as `EVALUATION_LANGSMITH_API_KEY`; do not put it in API/Coolify defaults,
images, arguments, browser bundles, CI secrets or a committed file. No `.env.local`
auto-loading is performed by this command.

With that approval, a clean `ENVIRONMENT=development` process may invoke:

```bash
uv run python -m app.bootstrap.evaluation_export path/to/summary.json --authorize-export
```

The supported endpoint is fixed to `https://api.smith.langchain.com/runs` and project
`portfolio-synthetic-evaluations`. Regional/self-hosted destinations and org-scoped
keys needing a workspace are not implemented. Review them before extending the
contract. Active `LANGSMITH_*`/`LANGCHAIN_*` overrides are rejected; the evaluation
key has a separate prefix. No global client configuration is changed.

Only the six validated summary fields, fixed model `gpt-6-luna`, fixed tags/name,
a newly generated evaluation UUID and the export timestamp are sent. The timestamp
is export time; it does not pretend to reconstruct a detailed execution trace.
Inputs/outputs are empty and explicitly hidden. No prompts, answers, source text,
errors, arbitrary labels, visitor/run/session IDs, attachments, SDK runtime inventory
or environment metadata are forwarded. The model label is a repository invariant,
not evidence that every case called the provider.

LangSmith 0.14.9 was already resolved transitively; it is now a direct pinned
dependency at the same version, with no package-version upgrade. A short-lived SDK
client uses one synchronous request, no SDK/HTTP retry, no background batch queue,
no proxy-environment discovery and no redirects. Connect/read timeouts are 2/5s;
DNS/OS behavior can exceed socket timeouts, so these are not a hard wall-clock SLA.
The session is closed after success/failure. Errors become `unavailable` and CLI
exit 1, without printing response bodies. Do not automatically retry: if the server
accepted a request before disconnection, a repeated command creates another UUID/run.

## Boundaries and evidence

`application/evaluation_export.py` owns the validated summary and exporter port;
`infrastructure/evaluation_export.py` maps it to the SDK; bootstrap owns CLI/config
composition. Existing AST/cycle and negative-fixture tests apply without new layer
exceptions. No HTTP, SSE, OPS or backoffice schema changed.

Local tests exercise the real SDK's serialized payload against a synthetic transport,
closed schema, explicit opt-in, disabled no-client behavior, scope/production rejection,
foreign destinations, redirects, no retry, safe failures and cleanup. They do **not**
prove an external account accepts the payload or its retention/access configuration.
No real LangSmith export was performed.

Official references inspected for this implementation:
[input/output and metadata privacy](https://docs.langchain.com/langsmith/mask-inputs-outputs),
[manual API tracing](https://docs.langchain.com/langsmith/trace-with-api).

This feature follows the source historically labeled `v1.1.0`, commit
`02b6f2784564669597fe8a4c2adf53bf807737a6`. Use the exporter's actual reviewed commit
in a compatibility manifest; it was not present in that earlier evaluated source.
The owner's later tag normalization does not change those historical facts; see
[release-reference policy](../README.md#verification-and-evidence).
