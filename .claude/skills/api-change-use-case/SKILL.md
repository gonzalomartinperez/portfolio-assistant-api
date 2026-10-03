---
name: api-change-use-case
description: "Implement or review API application rules, conversation/session ownership, rate and cost limits within the six-layer architecture. Use for business-policy changes; streaming, corpus ingestion and schema migrations have narrower workflows."
---

# Change an application use case

Read [AGENTS.md](../../../AGENTS.md) unless already loaded. Establish whether the
request authorizes implementation or only inspection. A review produces findings,
not edits or GitHub mutations. Inputs: desired observable behavior, affected
operation and compatibility expectations; inspect existing tests before asking
for information the repository already supplies.

1. Trace the operation from [HTTP](../../../app/presentation/http.py) through
   [application](../../../app/application) to its injected persistence/provider port.
   Use [architecture](../../../docs/architecture.md) for transaction/lifespan rules;
   read [coding conventions](../../../CONTRIBUTING.md) when changing code.
2. Put invariants in domain and orchestration/consumed ports in application.
   Neither imports ai, infrastructure, presentation or bootstrap. AI must use
   injected capabilities. The sole existing infrastructure exception is the CLI
   settings import from bootstrap.config; do not generalize it into a service locator.
3. For session or abuse-limit changes, inspect [conversation policy](../../../app/application/conversations.py),
   [atomic storage](../../../app/infrastructure/conversations.py) and the relevant
   [threat-model](../../../docs/threat-model.md) section. Ownership is checked on
   every operation; a model or prompt never authorizes access. Concurrent limits
   and usage reservations belong in database transactions, not in-memory counters.
4. Change one complete vertical slice when authorized. Preserve neutral Latin
   American Spanish and natural US English behavior. Translate dependency errors
   at boundaries and keep sensitive content out of logs/public errors.
5. Follow [verification commands](../../../docs/local-development.md#verification):
   architecture checks and pure behavior tests first; use isolated real services
   for ownership, concurrency, accounting or persistence effects. Report actual
   assertions and results, not only fixture answer text.

Deliver changed behavior, boundary/transaction decisions, tests and remaining
risks. Stop dependent work for an incompatible v1 change or missing authority;
continue unrelated safe work. Do not reset a dirty tree, edit sibling repositories,
raise budgets, or treat this skill as permission to commit, merge or deploy.

Conversation context is session-local untrusted data, capped at 12 earlier turns
and 8,000 characters. Never promote visitor claims or prior assistant text into
public evidence. See [conversation evaluation](../../../docs/conversation-evaluation.md)
and its real ownership/history regression before changing these bounds.
Test topic switches as well as pronouns: an example of a newly named employer must
replace the previous topic, while a later reference should retain the visitor's
latest refinement. Never use assistant-generated claims as retrieval anchors.
