# Public knowledge and GraphRAG

PostgreSQL owns source manifests, immutable revisions, chunk hashes, exact 64D
fixture vectors and the active corpus pointer. Neo4j is a rebuildable projection.
Conversation/checkpoint tables are separate from this approved public corpus;
chat history never becomes retrieval knowledge or long-term memory.

## Model and provenance

`Entity` nodes carry a kind: Project, Role (a public employment entry named by
company), Technology, Contribution, Education, Institution or PublicDocument.
`Document` nodes identify versioned chunks. `RELATES` edges carry a reviewed
predicate (`USES`, `CONTRIBUTED`, `AT_INSTITUTION`, `DOCUMENTED_IN`), corpus version,
supporting chunk ID, line span and public URL. `SUPPORTED_BY` links entities to
source chunks. Relationships are extracted only from explicit fields in the
allowlisted TypeScript sources; arbitrary source prose is not turned into facts.
The extractor is deliberately limited, not a general TypeScript parser.

The graph can traverse Project → Technology ← Role to retrieve evidence from a
role sharing a documented technology. This does not assert that the employer
owned the project or that the same contribution occurred in both places.
Every returned chunk is independently checked against PostgreSQL provenance and
hashes. Context is at most five chunks / 22,000 characters. Queries are fixed,
parameterized templates with limits and two-second transaction timeouts.

## Selection and cost

Hybrid uses deterministic lexical anchoring and exact vector search for ordinary
facts. Relationship cues in English/Spanish enable graph expansion. No routing
LLM is called. Graph outages fall back to verified lexical/vector evidence and
emit a redacted operational warning. Readiness still reports graph unavailability
because the deployment promises relationship retrieval.

The real graph is retained both for relationship behavior and hands-on engineering.
It costs a second database, rebuild/backup procedures and roughly hundreds of MiB
of idle memory. These costs are measured locally; VPS sizing remains unverified.

## Indexing and recovery

A PostgreSQL advisory lock serializes indexing across both projections. The
version includes the full source commit and parser version. Both projections
finish before activation; graph writes use one transaction. Empty/oversized
corpora fail closed. Same-version retries are idempotent. A failed staging
version leaves the old active corpus intact; rerun the same approved commit.
Old versions remain available for investigation and rollback; deletion is an
explicit operator action, not a destructive automatic migration.

Source files are literal blobs from the sole approved public repository, never
executed. The allowlist rejects symlinks and other file modes; blob size is checked
before reading. Git commands have timeouts, noninteractive credentials, no global
URL rewrites and no redirects on the fixed HTTPS source. No arbitrary URL input,
private export, recursive submodule or model-generated query is supported.

## Evaluation

Run `uv run python -m scripts.evaluate_retrieval` against the documented isolated
fixture environment. `evals/retrieval.json` covers direct facts, relationships,
shared-technology paths, ambiguity and no-answer cases in both locales.
`evals/fixture-results.json` records actual vector/graph/hybrid outcomes and total
retrieval latency, including the evaluation harness's driver setup. Pass means
required source paths and evidence text were retrieved, not that a model produced
a correct answer. Hash embeddings are a transport/development fixture and are
not a semantic embedding quality claim. Hybrid acceptance is enforced in CI;
we report weaker individual strategies rather than weakening the test cases.

## Measured strategy comparison · 2026-09-27

| Strategy | Evidence checks passed | Median retrieval ms |
| --- | ---: | ---: |
| vector | 4/8 | 126.8 |
| graph | 7/8 | 253.1 |
| hybrid | 8/8 | 110.7 |
