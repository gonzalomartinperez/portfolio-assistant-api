# Bounded real-provider smoke — 2026-10-17

## Scope and provenance

Separately authorized local test, with an aggregate USD 0.50 ceiling covering corpus
indexing, query embeddings and generation. No CI paid calls, external tracing,
registry publication, production deployment or public-assistant activation occurred.

- Product source: immutable `v1.1.0`, API
  `02b6f2784564669597fe8a4c2adf53bf807737a6`, extracted with `git archive`.
- Read-only public portfolio corpus:
  `776ee8613d3cc78bc3afb5a4609d5edbfd16ada3`, exactly 12 committed approved files.
- OpenAI `gpt-6-luna`, `medium`; `text-embedding-3-small`, 1,536 dimensions.
- Python 3.14.8, WSL Linux x86_64, fresh isolated PostgreSQL/pgvector and Neo4j.
  This is not a VPS, authenticated backoffice UI or physical-device benchmark.

An ignored invocation-specific transport guard wrapped the real SDKs without
changing product prompts, payloads or provider behavior. It permitted only the
two official HTTPS endpoints, exact models/effort, streaming/store=false, bounded
inputs/outputs and no tools. It reserved a conservative upper cost **before** each
request, including indexing, and never refunded uncertain requests. Unknown calls,
redirect destinations, excessive counts and the synthetic visitor email were rejected
before transport. SDK retries were zero. This guard is external test instrumentation,
not a new built-in application dollar limiter.

## Actual results

Six bilingual development cases covered technology evidence, project achievements,
recruiter utility with a synthetic volunteered email, contact, non-public facts and
architecture/accessibility experience. All six HTTP/SSE flows observed
`run.completed`; five used the actual model and one private-information question
was answered locally by policy, without provider generation.

| Measurement | Observed result |
| --- | --- |
| Provider generation requests | 5 |
| Index / query embedding requests | 95 / 5 |
| Stored public chunks / unique embedding cache entries | 96 / 95 |
| Semantic vector dimensions | 1,536 for all 96 chunks |
| Active corpus versions | 1 |
| Extracted graph facts / supported graph relationships | 278 / 446 |
| Graph relationships without a support document | 0 |
| Citation records checked against chunk ID, URL, spans, content hash and source SHA | 19 |
| Usage-derived cost estimate, rounded-up persisted ledger | USD 0.003678 |
| Conservative cumulative guard reservation / ceiling | USD 0.13834850 / 0.50 |
| Unsettled ledger reservations | 0 |

The ledger recorded 28,513 indexing input tokens, 113 query-embedding tokens,
19,466 generation input tokens and 2,213 output tokens. The estimate uses reviewed
standard rates and per-request rounding; it is **not** an invoice or account balance.
Pricing references:
[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[pricing](https://developers.openai.com/api/docs/pricing),
[embedding model](https://developers.openai.com/api/docs/models/text-embedding-3-small).

First HTTP delta by case: 8,756.51; 2,450.63; 2,899.51; 4,872.99; 71.65;
3,509.91 ms. Total durations: 10,202.57; 5,700.53; 4,996.42; 6,666.09; 100.57;
6,009.71 ms. The fast fifth case was local policy. Do not describe this mixed
six-case sample as provider p95, browser responsiveness or an optimization gain.

Manual reading found coherent English/Spanish responses, useful evidence-led recruiter
answers, qualified reported achievements and no repetition of the synthetic email.
The model distinguished responsive interfaces/design-system work from unsupported
formal accessibility-audit claims. The unavailable private facts received an honest
short abstention. Citation **provenance** was checked automatically; this is not an
independent exhaustive claim-by-claim factuality score. All five retrieval logs used
hybrid retrieval with graph expansion false: this run does not establish live
multi-hop GraphRAG quality. The graph projection was populated and checked separately.

## Deletion, retention and limits

The maintained HTTP harness created normal anonymous sessions, CSRF-protected
conversations, unique generation idempotency keys and deleted every test session.
Afterward sessions, conversations, messages, runs and all checkpoint content tables
contained **zero** rows. Six already-cleaned checkpoint tombstones remained under
the intentional ten-minute late-write protection; they are not transcript content.
Usage and aggregate operational facts remain by design. The owned local containers,
network and public-data fixture volumes were removed after inspection.

Raw answers and private driver diagnostics remain ignored/local, not CI artifacts or
public screenshots. Redacted receipt schema 1 is locally retained at
`artifacts/live-v110-2026-10-17/receipt.json`, SHA-256
`61b91f9441d3099754d5530f5c7ac69a30f7da731ddf9f4873c27b89a6cf861d`.
It records driver provenance and counts, without credentials, prompts or answers.

This is six cases, **not a repeat of the historical 244-turn evaluation**, not a
holdout score, and not exhaustive proof of the RAG bank or safety. Continuous source
watch, web search, cancellation under a paid stream, effective production headers,
live OAuth, backups and VPS capacity were not revalidated by this smoke. The
[Neo4j image production blocker](neo4j-release-blocker-2026-10-17.md) remains open.
