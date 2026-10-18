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
