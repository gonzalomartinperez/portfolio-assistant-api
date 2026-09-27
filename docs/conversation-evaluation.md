# Conversational behavior and evaluation

## Implemented boundary changes

The application loads at most six earlier turns after claiming the authorized run.
SQL binds both run and conversation, excludes the newly submitted question, checks
session expiration, and limits each row to 1,000 characters. Application policy
keeps at most 3,000 history characters. Prior assistant text and visitor job
requirements are untrusted context, never public knowledge. Deletion and checkpoint
cleanup retain their existing ownership and retention behavior.

LangGraph receives this plain application contract. Deterministic follow-up
resolution uses the latest substantive visitor topic for retrieval; unrelated new
questions discard that retrieval reference. The current question and labeled history
reach the provider separately from evidence. Context evidence is capped at 19,000
characters so history fits the existing conservative input reservation without
increasing budgets or adding routing/model calls. Before provider I/O, the final
JSON-escaped message text is measured in UTF-8 bytes, including 1,024 bytes of
framing allowance, against the existing 110,000-token conservative input ceiling.
Oversized serialized input fails safely without calling the provider; any prior
reservation remains held under the existing conservative failure policy. Existing 500-token model output
and 12,000-character application bounds remain; live completeness needs evaluation.

Profile overview retrieval prioritizes public profile content. Professional
questions exclude repository editorial/development instructions. Explicit employer
questions exclude candidates without that employer, a conservative precision choice
that may miss continuation chunks without repeated names. Metrics retain reported
values and qualifiers together. Fixture output quotes readable source prose rather
than raw TypeScript, and its citations match emitted excerpts. It remains an excerpt
renderer, not an intelligent model simulation; it cannot demonstrate nuanced role
assessment or deeper technical explanation.

Provider instructions specify answer-first, natural bilingual responses; personal
versus team attribution; evidence/transferability/gaps in role fit; restrained tone;
specific uncertainty; and no commitments or hidden/internal output. These prompt
changes are not authorization controls or proof of model compliance. Tools remain
absent. Citation provenance is deterministic; live claim-level attribution is still
a review requirement, not a guarantee from attaching retrieved sources.

## Reproduce without paid calls

After the README's isolated fixture database/migration/index setup:

```sh
uv run python -m scripts.evaluate_conversations --output artifacts/conversations.json
uv run python -m scripts.evaluate_retrieval
TEST_INTEGRATION=1 uv run pytest -q
```

The conversational runner owns a fixture-configured HTTP server on an ephemeral
loopback port; it does not accept an arbitrary server URL. It creates and deletes
its own session, records actual SSE first-delta and terminal timings, answers and
citations. It uses real databases and the pinned public corpus. Run separately from
load/integration tests for comparable latency. No real provider is selected.

## Before/after evidence

Actual runs: [before](verification/conversations-before.json) and
[after](verification/conversations-after.json), 20 turns each, English and Spanish.
The baseline used the original live loopback fixture server; the maintained runner
now controls provider selection. Both runs used the same approved public revision.
Timing observations are local and not controlled performance comparisons. Before:
median first delta 257.6 ms, completion 462.5 ms. After: first delta 349.5 ms,
completion 531.8 ms. Both completed 20/20 turns. Raw code fences fell from 17/20
to 0/20. The extra bounded history read and different host contention mean this
is not a performance improvement claim.

| Case | Before | After | Residual limitation |
| --- | --- | --- | --- |
| Tell me about Gonzalo | Generic insufficient-evidence response | Public profile intro and summary, AI Software Engineer and concrete project context | Quoted fixture prose, not model-generated tone |
| Give me an example after Rampy | Editorial guidance unrelated to prior answer | Employer context retained and contribution excerpt returned | Fixture may repeat rather than choose a new example |
| Performance evidence | Institutional ranking/editorial content | Startup and workflow figures with owner-measured/estimated qualifications | Public reported figures are not independently benchmarked |
| Spanish overview | Raw source syntax | Readable attributed Spanish profile prose | Translation/deeper explanation still needs live evaluation |
| Make it shorter / Hazlo más breve | Unrelated content | One bounded excerpt from the same topic | Deterministic excerpt shortening only |
| Salary / private-data request | Unrelated professional excerpts | Abstention with no evidence citations | Specific helpful refusal wording needs live review |

Review rubric for future runs: score each of usefulness, relevance, grounding,
question-appropriate completeness, clarity and continuity from 0 (fails), 1
(partial), 2 (meets). Do not combine fixture scores into a model-quality claim.
The deterministic improvements establish context transport, relevant evidence and
readability. Role-fit reasoning, original technical explanation and personality
remain **not evaluated with a live model**. Fail any invented professional claim,
unsupported metric, private information or invalid citation regardless of total.

## Separately authorized live procedure

Before execution, obtain explicit model/cost authorization, verify current official
pricing, choose a model and a small total ceiling (proposal: at most USD 1 for the
first review), and configure conservative atomic reservations accordingly. Do not
raise repository budgets to make a run pass. Keep secrets server-side and external
tracing off. Use isolated sessions, the approved public corpus and the same cases,
plus held-out paraphrases, corrections, unsupported role requirements and retrieved
injection fixtures. Review both languages and score the six rubric dimensions.
Record actual usage, first useful output, terminal latency, source attribution and
failures; stop on the approved spend boundary. Human review is required before any
claim of improved live-model usefulness or injection resistance. No such run has
been authorized or executed in this phase.

### Reviewer scores for representative fixture output

These are engineering-review judgments on the recorded excerpt renderer, not
model evaluations or independent human ratings. Columns use the 0–2 rubric above;
continuity is omitted when a single-turn case cannot measure it.

| Recorded case | Usefulness | Relevance | Grounding | Completeness | Clarity | Continuity |
| --- | --- | --- | --- | --- | --- | --- |
| Overview before → after | 0 → 2 | 0 → 2 | 2 → 2 | 0 → 2 | 1 → 2 | — |
| Rampy follow-up before → after | 0 → 1 | 0 → 2 | 1 → 2 | 0 → 1 | 0 → 2 | 0 → 2 |
| Metrics before → after | 0 → 2 | 0 → 2 | 1 → 2 | 0 → 2 | 0 → 2 | — |
| Role fit after | 1 | 2 | 2 | 1 | 2 | — |
| Learning gaps after | 0 | 1 | 2 | 0 | 2 | — |

The low learning-gap/role-fit completeness scores are deliberate: source excerpts
do not perform that reasoning. Do not hide these limitations behind aggregate
scores. An authorized live-provider review is the next quality decision gate.
