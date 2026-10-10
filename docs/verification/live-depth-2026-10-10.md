# Authorized live evaluation · 2026-10-10

Scope: API implementation and isolated local evaluation. The portfolio, backoffice
and vps-ops were read-only. No production activation, main promotion, image
publication or paid fallback. Raw artifacts remain ignored under `artifacts/`;
only manifests and reviewed summaries belong in this public repository.

## Revisions and method

- Baseline API: `be47979d302471121144a9bf53f23229de9190de`.
- Public corpus: `afea06a04650db65059a8900d58554b8952b2c99`,
  version `afea06a04650db65059a8900d58554b8952b2c99-semantic-v7`.
- Baseline manifest: `evals/live-depth-2026-10-10.json`, committed at
  `2e81060a6af8305db44de1886717310b7b846af7`.
- First revalidation source: `586af7e61e99a02053e34f5981ce3fba33a6bfaf`;
  final language/qualification source: `757ad40f2ca89e81e97d5fbbe69e2b6f8d06163b`;
  adjacent-role source: `0c52d82487fd70bc18377753caebbab2d72cf2aa`.
- Python 3.14.8, uv 0.13.0, actual OpenAI `gpt-6-luna`, medium effort,
  semantic `text-embedding-3-small` vectors with 1536 dimensions.

The baseline contains **244 turns**: 200 independent bilingual questions
(one direct question per 100 intent families in each locale), 20 adversarial
questions and six four-turn conversations. That is 226 scenarios, not 244
independent intent families. Calls use real session/CSRF/HTTP/SSE adapters and
persistence; observation hooks record retrieval and usage without changing answers.
No automatic generation retries. The total isolated experiment ceiling is USD 0.50.

There were 236 actual generation calls and eight local evidence abstentions.
243 HTTP terminals were observed as completed. One interrupted harness result was
recovered from its completed PostgreSQL message **without another model call**;
its original HTTP terminal and timings remain unobserved. No causality is claimed
for that process interruption. Frozen baseline SHA-256:
`4d45fdf079e4167966e660b43f7152386999c8bfd89ce7ba4fabe4b2bb1991c7`.

All 244 stored results passed canonical marker validity, citation provenance
membership and emitted-final/persisted-history equality checks (the recovered
case checks persisted content only). These checks do **not** establish that every
claim follows from its cited span. Qualitative review was agent-assisted, not an
independent owner review or a statistically calibrated model-quality score.
Original development/holdout labels remain recorded, but reviewed families are
now exposed: post-fix results are exploratory regressions, not untouched holdout.

## Findings and changes

| Observed problem | Implemented response |
| --- | --- |
| Portuguese answer despite English resolved locale | Server-resolved language is authoritative in the provider prompt; an initial bounded prose guard detects common unsupported languages. |
| First-person career facts attributed to assistant or visitor | Explicit third-person attribution and separate rules for labelled requested drafts. |
| Historical provider experience offered as current fallback | Explicit operational policy: OpenAI only, no fallback or automatic generation retry. |
| Graph-first comparison omitted Pequeverso | Reserve evidence for each named subject actually present in verified public spans. |
| Education answers omitted completed qualification | Preserve the verified first education span for degree/education queries. |
| Recent-role comparison missed an employer | Prefer distinct dated public company spans before filling the bounded evidence set. |
| Public Infisical experience blocked as credential disclosure | Separate professional secret-management questions from disclosure requests; compound credential requests remain blocked. |
| English named-topic switch retained Rampy | A specific example **from** a named subject is a new topic, matching existing Spanish behavior. |
| Answers invented sync capabilities from portfolio docs | Explain supplied versioned indexing, no autonomous browsing or visitor-driven corpus changes. |

The first output guard reused low-accuracy all-language input detection. A corpus
prefix replay exposed false rejection of valid technical and short English/Spanish
text. It was replaced before merge with a separate normal-accuracy six-language
guard (English, Spanish, Portuguese, French, German, Italian), requiring at least
eight words, confidence >=0.95 and margin >=0.30. Replaying all 244 baseline
prefixes then rejected only the observed Portuguese answer. The isolated six-language
prototype took 0.25 seconds across 244 prefixes and reached 50,768 KiB process peak
RSS; this is not a production container-memory guarantee.

The provider buffers the first 256 characters (or a shorter completed response),
checks at most the first 512 characters and then streams normally. This introduces
real first-output latency, not a fake delay. It does not guarantee detection of
all unsupported languages, very short text, or a language switch later in a response.
The authoritative prompt remains necessary; no unsupported text is substituted with
a second paid generation. Rejection closes the provider reader and preserves an
uncertain cost reservation until usage can be reconciled.

## Revalidation and verification

The first targeted run contained 41 turns (40 model calls, one local abstention):
40 completed and one returned `generation_failed` before any visible delta.
It also exposed a degree omission for French input and company/date fields
spanning adjacent chunks. The original terminal failure is retained; its precise
provider error was not captured, so it is not labelled conclusively as a guard
rejection. Offline replay separately established the guard's false-positive defect.

After fixes, 13 targeted turns completed, including supported technical prose,
short/abstention answers, French education input, Portuguese request with English
output, institutional names, privacy and four-turn language continuity. Two more
real role comparisons then included Rampy, Teamcubation and Cooperativa Obrera
with dates and contribution qualifiers after the adjacent-span correction.

Total: **300 evaluated turns, 290 actual generation calls, ten local abstentions**.
The final shared experiment ledger accounted USD **0.227129**, including USD0.10
in uncertain reservations (one predates this suite). Settled total is USD0.127129;
no unknown provider usage was silently counted as free or retried automatically.
This remains below the USD0.50 ceiling. See the exact per-run revisions, hashes,
counts and ledger deltas in [machine-readable evidence](live-depth-2026-10-10.json).

Final full local suite: **319 tests passed in 14.70 seconds**, including 25 real
PostgreSQL17.11/pgvector0.8.7 and Neo4j5.26.31 tests. Ruff, formatting and strict
mypy passed. An earlier test execution began before Neo4j completed startup and
had two connection-handshake failures; all25 integration tests passed after
readiness in 41.69 seconds, followed by the full final run above. Test failures
were not suppressed. Contract export left v1 artifacts unchanged.

## RAG and database audit

The pinned index contains 12 approved files, 76 chunks (75 distinct content hashes),
all with semantic vectors. Incremental sync embedded 16 changed chunks and reused
ten files. The public embedding cache has 85 entries and contains public-source
embeddings, not conversation/query content. Retrieval uses bounded graph and vector
results, at most five verified evidence spans; there is no arbitrary model Cypher.

The active graph has 76 Document nodes, 140 Entity nodes and 502 RELATES edges.
All edge backing-document IDs belong to active PostgreSQL chunks; all checked
source spans and URLs resolve to the pinned revision. The index reports 274
extracted facts: overlapping chunks and bilingual support produce more relationships
than facts, so these are different counts. No Precision/Recall@k claim is made
without labelled relevance judgements.

After the baseline, deleting owned sessions and draining durable cleanup left zero
sessions, messages, orphan checkpoint threads and pending cleanup entries. Recent
cleaned tombstones may remain for ten minutes to protect against late writes.
The spend ledger survives deletion without retaining conversation credentials;
retention/pruning scheduling remains a vps-ops responsibility. The final audit after
all300 turns again found zero sessions, messages, orphan checkpoint threads and
pending cleanup; chunk/cache/graph counts were unchanged. The exact authorized
key was absent from14 raw JSON artifacts, and the redacted tracked/history secret
scan reported no known-pattern findings. These checks are not a universal secret detector.

Paid evaluation used the existing isolated PG17/pgvector0.8.1 and Neo4j5.26.17
fixture. New-code offline/real-service tests and production-image smoke use the
separately owned PostgreSQL17.11/pgvector0.8.7 and Neo4j5.26.31 fixture. These are
distinct compatibility checks; paid evaluation is not a latest-image deployment test.

## Cost and timing

Baseline ledger delta: **USD 0.096218**, including 236 generations and 238 query
embeddings. Semantic indexing occurred before its ledger-start snapshot and is
accounted separately in the shared experiment ledger. Baseline end accounted total
was USD 0.153519, including an earlier uncertain USD0.05 reservation; settled total
was USD0.103519. Cost is calculated from provider-reported usage and reviewed prices
(input USD0.10/M, output USD0.50/M, embeddings USD0.02/M), not an invoice.

For the 235 generation cases with observed timings, first delta p50 was
2447.59 ms and empirical p95 5177.75 ms; total p50 3826.72 ms and p95 8824.00 ms.
These are sequential WSL/Linux local HTTP observations including remote OpenAI and
semantic retrieval. Targeted revalidation changes the question mix, so it cannot
prove a general latency improvement/regression. No field or physical-device claims.

## Acceptance and remaining gates

| Requirement | Evidence / remaining condition |
| --- | --- |
| More than 200 actual evaluated turns | 244 baseline turns; generation vs local abstention distinguished above. |
| Rich, grounded bilingual answers | Real qualitative review and targeted regressions; not all1000 bank cases independently scored. |
| OpenAI only, medium effort, no automatic retry | Runtime configuration, provider request tests and real capability-policy cases. |
| Dynamic public portfolio synchronization | Versioned incremental index and existing recovery/freshness tests; no production worker scheduled here. |
| Age, nationality and personal details | Public city/timezone supported; unpublished age/nationality remain unknown. No private career-ops ingestion. |
| Session isolation, CSRF, cancellation and persistence | Existing real-service regressions plus this evaluation's final/history equality and cleanup audit. |
| RAG and database integrity | Semantic vectors, graph backing spans, active-version audit and checkpoint cleanup. |
| Production image readiness | Local/CI build and smoke evidence; security acceptance below remains separate. |
| VPS/Coolify deployment | Not performed; owned by vps-ops and separately authorized. |
| Native portfolio/backoffice browser integration | Separate owners and future paired browser verification; assistant remains disabled. |
| Dependabot and protected integration | Only protected task PR into develop; automation activation limitations remain documented. |

The original role-depth conversation also lost previously retrieved Kubernetes
context in a later followup. Bounded evidence does not ensure universal semantic
continuity; broader labelled multi-turn retrieval evaluation remains a followup.
Ambiguous “what languages does he publish?” can ask about publication language
rather than spoken proficiency; clarify intent rather than fabricate a score.

Known release gates remain: vendor image vulnerability acceptance/remediation,
real OAuth/browser pairing, effective Coolify proxy headers/disconnects, off-server
backup restoration, migration-compatible rollback, shared-VPS capacity and owner
review of exposed/independent evaluation samples. No high-availability or
production-readiness claim follows solely from this report.

During the final meaningful source check, the portfolio had advanced to
`ddb0b89e5f9d46b416fb9fe04d14d5833d78d8be`. This suite deliberately remains pinned
to `afea06a` for reproducibility; it is not evidence of answers against the newer
revision. Existing synchronization recovery tests exercise updates independently.

Integration is through [PR43 into develop](https://github.com/gonzalomartinperez/portfolio-assistant-api/pull/43).
Current-head CI must pass before merge; a pass for an earlier head does not satisfy
that gate. Required strict `checks` and administrator enforcement were verified
through the live GitHub API; zero approvals are configured. No bypass is used.

Official references: [OpenAI evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
and [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna).
