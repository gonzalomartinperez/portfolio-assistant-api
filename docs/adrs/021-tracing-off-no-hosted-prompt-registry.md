# ADR021: External tracing stays off; no hosted prompt or dataset registry

Status: accepted (2026-11-14, master plan task M2-6b, decision PAA-D8).

## Context and problem

The ecosystem standard (section 12.3) proposes LangSmith as the default home for
traces, eval datasets and prompt commits. This service answers anonymous visitors on a
public portfolio. Visitor questions, conversation history and the assembled prompt
with retrieved evidence would all leave the service if a hosted tracer were enabled,
and the privacy decision recorded in the threat model is that visitor text never
leaves the service except in the single generation call to the configured model
provider. The settings validator in `app/bootstrap/config.py`
(`Settings.safe_configuration`) already rejects every LangSmith and LangChain
tracing switch, and only scalar, allowlisted OpenTelemetry attributes may go to a
private OTLP endpoint (`docs/private-observability.md`).

Prompt versioning still needs a registry, so that every quality number can be tied to
the exact prompt that produced it (PAA-D7, M2-6).

## Considered options

1. **Hosted tracing and prompt hub (LangSmith).** Rich trace UI, prompt commits,
   hosted datasets. Sends visitor text and evidence to a third party; adds a vendor
   key to the runtime; duplicates the golden set outside git (two sources of truth).
2. **Self-hosted tracer (Langfuse or similar) now.** Keeps data private, but needs
   a deployed service and storage before the VPS exists (MV) and adds an operational
   surface with no current consumer.
3. **Tracing off; git is the prompt and dataset registry (chosen).** Prompts live in
   versioned files with a lock file of hashes (ADR014); eval items, baselines and
   reports live in `evals/`; runtime observability stays scalar-only through the
   existing private OTLP path.

## Decision

Option 3.

- External tracing stays disabled by code: `Settings.safe_configuration` keeps
  rejecting `LANGSMITH_TRACING`, `LANGSMITH_TRACING_V2`, `LANGCHAIN_TRACING` and
  `LANGCHAIN_TRACING_V2`. No tracing SDK key is configured in any environment,
  including `eval-live`.
- Git is the prompt registry: prompt files, `prompts.lock` and the `prompt_version`
  recorded in usage logs and eval reports (ADR014). LangSmith prompt commits are not
  used.
- Git is the dataset registry: the golden and full sets, qrels, cassettes and
  baselines are committed under `evals/`; nothing is mirrored to a hosted dataset.
  This is the documented deviation S5 from the ecosystem default.

## Consequences

- Good: no visitor text or evidence reaches a tracing vendor; one source of truth for
  prompts and datasets; every eval report can be reproduced from a commit.
- Bad: no hosted trace explorer. Failure analysis uses the eval reports (counts per
  stratum, failing item IDs) and private, scalar runtime metrics. Error analysis of
  real traffic after Phase V needs a private store first.
- Revisit when: the VPS exists and the owner wants a self-hosted tracer with a
  redaction policy, or the sibling assistant API standardizes on a different
  registry. Any change needs a new ADR and an owner decision because it touches the
  privacy policy.

## Confirmation

- The settings tests in `test_grounded_assistant.py` and
  `test_global_automatic_tracing_remains_rejected` in `test_evaluation_export.py` fail if any tracing switch is
  accepted by the settings validator.
- The prompt lock test from ADR014 fails if a prompt file changes without its lock
  entry.
