# Bounded technical web context · 2026-10-13

This increment changes the API only. The portfolio, backoffice and private vps-ops
were references; no production deployment, publication or assistant enablement occurred.
The [tool policy](../bounded-web-context.md) describes the implemented boundaries.

## Real evaluation and what it proves

The frozen manifest `evals/web-context-2026-10-13.json` contains **264 turns**:
200 bilingual direct questions from 100 previously reviewed intent families, 20
adversarial questions, six four-turn conversations, fourteen technical-complement
questions and six scope/security questions. These are exposed regressions, not fresh
holdout. The corpus was frozen at public portfolio
`f2fca923a4d109937378e0f12779f817688fd537`; it was the inspected public main revision
at experiment start. A later source check observed `e770c3894732f69f96e45c2459a7c2b341bb29aa`.
The experiment does not silently substitute that later revision or claim instant sync.

At API source `e3b1781ac11728dafd3cd2e51aa35fe7c97c5d6c`, all264 HTTP/SSE turns
completed, with **256 actual GPT-6 Luna generations and eight local policy responses**.
Every observed final answer matched its authorized persisted history; citation markers
and immutable source membership passed. Those checks are not factual-entailment scores.

Response text was reviewed by the implementation agent for relevance, attribution,
qualifiers, privacy, scope and language; source support was spot-checked. No independent
owner review or calibrated accuracy percentage is claimed. Review caught two semantic
failures despite successful HTTP terminals: an editorial/language follow-up lost RAG
experience evidence, and a metric-classification follow-up omitted a design goal.
Both were fixed in pure context/ranking policy and revalidated in complete four-turn
sequences. Earlier failed or incomplete experiments remain recorded, rather than being
reclassified as passes.

Other observed fixes: retain named technical spans when generic portfolio documents
crowd the evidence window; separate external document links from career citation IDs;
remove only known attribution parameters; expose verified source URLs for explicit
reading requests; keep proper place names from switching English questions to Spanish;
explain the local no-automatic-generation-retry policy. Employer switches remain explicit,
while generic possessive examples, interview refinements and locale changes preserve the
visitor topic without treating previous assistant claims as evidence.

Post-fix phases: 24 live targeted turns, two real FastAPI generations using a public
cache seeded from an actual already-billed diagnostic, two four-turn continuity/metric
runs, and a final16-turn regression covering those sequences, employer switches,
capitalized locale, vendor-versus-employer and retry policy. Final16/16 completed:
15 model generations and one local policy response. Replayed cache data is clearly
separated from fresh cold search. See exact source revisions, raw-artifact hashes,
counts and timings in [machine-readable evidence](web-context-2026-10-13.json).

## Performance and cost

Sequential WSL/Linux observations, including remote OpenAI:

| Main264-turn run | p50 | Empirical p95 |
| --- | ---: | ---: |
| First visible delta, all turns | 3,674.73ms | 8,667.52ms |
| Completion, all turns | 5,236.62ms | 14,407.57ms |
| First delta, generation without web context | 3,580.45ms | 6,264.04ms |
| First delta, accepted web-context subset | 9,105.85ms | 12,748.52ms |

Successful warm topic lookups took about0.01ms; cold accepted lookups in that run
were about4.6–6.6s. This measures lookup reuse, not the entire response becoming instant.
Web context adds waiting and often produces longer answers. It is deliberately absent
from ordinary profile queries. Question mix, updated public corpus and host contention
prevent a controlled speedup comparison with older evaluations or exploratory runs.
No browser/field performance claim follows from these server observations.

The shared isolated experiment ceiling was USD2.00. The final ledger remained below
that ceiling, including indexing/query embeddings, generation, tool fees and uncertain
reservations. Actual final category totals are in the JSON storage audit. Four timed-out
exploratory searches retain full reservations; one interrupted generation also retains
its reservation. Known usage settles reviewed standard prices, not a provider invoice;
unknown charges are never counted as free. No automatic billed generation retry occurred.

## Services, cleanup and verification

Runtime: Python3.14.8, local uv0.12.10, frozen OpenAI3.24.0 and LangGraph1.2.13;
GPT-6 Luna requested with medium effort and text-embedding-3-small semantic vectors.
Owned services were PostgreSQL18.6/pgvector0.8.7 and Neo4j5.26.31, with isolated
loopback ports and a separate integration database. No other agent service was stopped.

The active public index contains89 semantic chunks /88 distinct hashes;88 public
embedding-cache entries. Its graph has89 Documents,141 Entities and442 backed
relations. Every checked relation's supporting document exists in active PostgreSQL
and its source revision/line range matches. Counts are not retrieval Precision/Recall.

Final cleanup found zero sessions, runs, messages, pending cleanup and checkpoint
threads. Recent cleaned tombstones remain briefly against late writes; the spend
ledger survives session deletion. Cleanup included test-owned remnants from an earlier
interrupted fixture-mode integration attempt. That attempt was stopped and is not a
pass; the later separate fixture database completed **407 tests in30.88s**. Ruff,
formatting, strict mypy, skills validation and unchanged contract export also passed.
24 raw JSON artifacts were checked for the exact authorized key with zero matches;
the redacted tracked/history known-pattern scan found none. Neither scan is universal.

The main long evaluation wrapper returned143 after recording all264 observed terminals
and its final ledger, without a traceback. Normal long-wrapper exit is therefore not
claimed. Short focused revalidations exited0, persisted results matched, and cleanup
was audited separately. Production-image lifecycle proof remains the required CI smoke.

## Remaining limits and rollout

- The approved portfolio corpus does not yet describe this assistant's internal stack
  sufficiently; answers correctly avoid attributing that stack from general web docs.
  See [the public-knowledge handoff](../coordination/portfolio-assistant-knowledge.md).
- Some broad project/role-overlap answers emphasize roles over named projects. Larger
  independent relevance judgements and full1000-case review remain future work.
- Hosted search availability, result versions and citation attribution can change;
  unapproved or unsupported results degrade to RAG-only answers. Citation presence
  does not independently verify a claim. No universal injection-resistance claim.
- Web remains off by default; production activation belongs to owner-approved vps-ops
  deployment. Real proxy/TLS/CORS, OAuth, phones and VPS capacity remain separate gates.

Reproduce routine evaluation through the existing `scripts.evaluate_assistant` commands
in [the evaluation guide](../assistant-evaluation.md), using an owned migrated/indexed
fixture and separately authorized paid mode. The deeper manifests freeze the reviewed
scenarios; ignored one-off runners/raw results are not portable production commands.
