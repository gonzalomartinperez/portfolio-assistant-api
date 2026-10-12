# Continuous public knowledge

The API owns one bounded sync worker, not a production scheduler. Start it locally
with `uv run python -m app.knowledge_watch` after migrations and initial indexing.
Fixture mode costs nothing. vps-ops decides its Coolify process/resource and credentials.

## Revision and freshness

The worker resolves only `gonzalomartinperez/portfolio` main, fetches immutable Git
objects and reads allowlisted blobs. It never modifies that repository, executes
source code, reads career-ops or follows alternate remotes/HTTP redirects. Its bare
checkout lives in temporary writable storage and is reconstructed after restart.

Every successful poll writes `knowledge_watch` before indexing. Polls continue while
one job projects the candidate; intermediate revisions coalesce. A process-level
advisory lock prevents duplicate workers; indexing has its own cross-process lock.
Activation checks the observed SHA under a row lock after both projections finish.
A superseded or failed candidate cannot replace the active revision. Each request
uses an immutable corpus version even if the active pointer changes during its turn.

With `REQUIRE_FRESH_KNOWLEDGE=true`, a different observed SHA or a check older than
90 seconds yields `knowledge_updating` before query embedding or generation. It does
not describe old facts as current. Polling defaults to 60 seconds: network/indexing
latency remains additional; this is not an instantaneous synchronization guarantee.
No fixture answer disguises a provider outage. The previous corpus stays available
for recovery, while current claims are withheld if freshness cannot be established.

Stop signals request cooperative cancellation between source/embedding operations.
Git calls are bounded to 30 seconds, embeddings to 20 seconds. The worker waits for
its active job; use at least 60 seconds of worker termination grace and verify the
actual Coolify behavior. API termination grace is separately documented.

## Embeddings and migrations

Migration 004 preserves the 64D fixture column and adds a nullable 1536D semantic
column, per-version provider/model metadata, full-text search and freshness state.
Do not rewrite old migrations. Old images reject unknown migration histories: an
additive SQL change alone does not establish image rollback compatibility.

Production OpenAI uses `text-embedding-3-small` and `gpt-6-luna` with medium reasoning.
Migration 005 persists each public embedding by content hash immediately after success,
so a failed candidate can reuse completed calls on its next attempt. Visitor query
vectors and transcripts are never cached there. Unchanged content hashes reuse semantic vectors. Queries use asynchronous provider
I/O so disconnect/cancellation closes pending work. Indexing uses a bounded sync SDK
in the dedicated worker. Both share the monthly ledger with generation; unknown
usage retains its reservation. No credentials or costs are decided by a model.

Hash vectors still support deterministic, free fixtures. Their lexical confidence
gate stays in place; semantic vectors do not require shared literal words. Real
semantic precision/recall remains unverified until paid evaluation is authorized.

## Portfolio owner handoff

Publish optional `public/assistant-knowledge.json` according to
[`contracts/knowledge.schema.json`](../contracts/knowledge.schema.json). It is an
additive public artifact, not a request to expose a private career-ops export.
Use approved facts with bilingual subject/text, stable IDs, verified dates,
source spans and personal/team/context attribution. Metrics preserve value, unit,
qualifier and optional baseline. City/country/nationality/dated age are optional;
never include street address, full birth date, private compensation or credentials.
Unconfirmed personal fields must remain absent.

The complete artifact must fit 500,000 UTF-8 bytes; each fact fits the embedding
bound; at most 300 facts and 500 total chunks are accepted. Schema validation,
duplicate identities and nonexistent committed spans fail the candidate before
paid embeddings. Source files remain capped at 60,000 bytes each, 80 files total.
The projection itself is cited from its immutable public Git blob. Its complete
fact objects are chunked intact, preserving qualifiers and attribution.

When present, structured facts replace regex-derived graph facts. Until the owner
publishes it, approved TypeScript/Markdown extraction remains operational and is
explicitly a compatibility path. Personal data in a validated public projection
becomes retrieval evidence; it is not guessed from location or automatically aged.
Starter questions come from available bilingual sections, not private transcripts.

Before declaring public freshness correct, the portfolio owner must reconcile its
public CV with the approved latest editorial revision and correct any unsupported
immediate-start availability copy. Availability remains conservatively withheld
until that separate content review is integrated; no sibling files are edited here.

## Security and maintenance

The API runtime role needs read access to `knowledge_watch`, not write access. The
worker needs separate narrowly scoped writes to knowledge tables, graph projection
and spend ledger. Schema creation stays with migration credentials. No admin HTTP
endpoint starts indexing. Runtime grants are in `deploy/runtime-grants.sql`; exact
worker login/secret delivery belongs to vps-ops.

Retired/staging versions are currently retained for recovery. vps-ops must measure
disk growth and define a reviewed pruning policy before long-running production;
never delete a version pinned by a live request or required for recovery.

Useful checks: `uv run pytest -q tests/test_grounded_assistant.py`, followed by
`TEST_INTEGRATION=1 uv run pytest -q -m integration` in the isolated fixture stack.
Evidence must distinguish source/activation correctness from live answer quality.
