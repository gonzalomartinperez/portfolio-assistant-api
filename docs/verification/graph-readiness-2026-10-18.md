# Bounded public graph readiness

Local verification of source `efee3df1ae0fe61821f41370decc1e6991f2ca8f`
observed intermittent first-read failures on fresh Neo4j fixtures. A sanitized
observer established `Neo.ClientError.Transaction.TransactionTimedOutClientConfiguration`;
it did not establish whether planning, execution or scheduling caused the timeout.
The one-CPU fixture also produced a successful worker run without a source change.
Those failed runs remain evidence, rather than retries relabeled as success.

The comparison bank separately matched its committed reference: vector 5/9,
graph 8/9 and hybrid 9/9. The release criterion is all nine authored hybrid cases;
weaker individual strategies remain reported. A temporary local executor incorrectly
required every comparative result to pass; its original failed receipt is retained.
Neither evaluation cases nor application acceptance thresholds were changed.

## Application behavior

`app/adapters/neo4j/read_queries.py` owns the two fixed relationship queries.
Index publication prepares those exact read queries after projection/schema/index
completion, before PostgreSQL activates the candidate. It reads at most three public
project/role names, first checking a PostgreSQL chunk identifier against Neo4j's
indexed document identity, then consumes direct and expansion results for each locale.
There are five transactions with five-second server timeouts, plus separately
bounded connection acquisition. This publication work never runs in a visitor's
generation request and cannot invoke a model. Failure preserves the previous active
corpus; candidate projections remain staging. An unchanged active-version sync also
prepares the reads, covering the worker's restart path without rewriting corpus rows.

Visitor graph reads retain their two-second transaction timeouts. Readiness executes
the subject/direct/expansion probes in **one shared two-second read transaction**;
it no longer certifies graph availability from connectivity alone. It checks the
PostgreSQL active pointer again after the probe, rejecting a concurrent change.
There is no cached ready flag and no repeated five-second preparation on health polls.
Read sessions use the configured database and the driver's read access mode; that
mode is a routing hint, not Neo4j Community authorization.

The pinned driver is 6.4.1. Since 6.2, implicit transactions can retry once when
the server marks an error idempotent; `max_transaction_retry_time=0` alone does not
disable that behavior. Index/API drivers and graph read sessions explicitly set
`disable_auto_commit_retries=True`. Client vendor telemetry is disabled separately.
See the [official driver transaction documentation](https://neo4j.com/docs/python-manual/current/query-advanced/).

## Acceptance and limits

Run the offline tests in `tests/test_graph_readiness.py`, then the real isolated
worker/corpus tests in `tests/test_content_root_integration.py` and the readiness
race test in `tests/test_integration.py`, using `TEST_INTEGRATION=1` and the documented
owned fixtures. They check complete result consumption, publication failure,
previous-corpus preservation, the unchanged two-second read budget, active-version
startup and concurrent pointer changes. Synthetic encoders are not model calls.

Use the same one-CPU/1536-MiB Neo4j fixture for the local counterfactual; preserve
the original failures and report actual cold and prepared outcomes separately.
Before admitting production traffic, vps-ops must verify effective readiness and
streaming after a cold start and dependency restart with its real resource allocation.
The [query-cache documentation](https://neo4j.com/docs/cypher-manual/current/planning-and-tuning/caching/)
explains parameter-shape and schema invalidation. Preparation does not guarantee a
cache hit for every question, eliminate eviction or establish a field latency SLO.

## Executed counterfactual

Source `b53cd1998e17c27a7b6ba17ac2317d9db6cfcfce` passed the fresh isolated
counterfactual on the same Neo4j one-CPU/1536-MiB ceiling. PostgreSQL used 0.5 CPU/
512 MiB; the host test process used core 3 at low priority. The worker/publication
and two readiness identity-race cases passed: 3 tests in 14.20 seconds. The complete
[hosted Quality run](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/39171935622)
separately passed all six required jobs, 794 offline tests and 47 real-service tests
(51.22 seconds). Neither count is substituted for the other environment.

The exact public producer `12e68c662b855422411ffdfd1d5334f6b4b0e086` was then
indexed with fixture hash64 vectors: all eight professional files, 12 approved
files total, 97 chunks, 282 extracted facts and 460 source-supported relationship
instances. Six English/Spanish × vector/graph/hybrid queries returned the correct
locale/root paths and immutable commit/line citations; each locale had five starter
questions. Resynchronization was unchanged, and the previous version remained retired.
The index's ledger row count stayed zero. Twenty fixture HTTP turns completed with
`run.completed`, followed by successful session deletion. This verifies transport,
provenance and fixture behavior, not semantic model quality or real visitor traffic.

The run ended at 22:31:10 UTC on October 18. Independent cleanup readback confirmed
the owned processes, containers, network and volumes absent, with all three ports
bindable. The owner-local execution receipt has SHA-256
`7401d6994eb6ca128a847b15a473796019e4276d631a3dad2a83553c6f334f31`;
the producer acceptance receipt is
`782ad302ae01a00669105ebe2e6db0c24dab6e4ef2fa6258e4050fc226421e3c`.
Original failed runs remain retained. No OpenAI request, production deployment or
registry publication occurred. The vendor-image security and VPS-only gates remain.
