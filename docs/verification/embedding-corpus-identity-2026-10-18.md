# Embedding corpus identity correction

The previous fixture/semantic versions for one source commit shared chunk IDs,
violating PostgreSQL chunk and Neo4j document uniqueness when changing providers.
New indexing namespaces IDs by corpus version, provider, model, dimensions and the
existing source/chunker identity. Citations, content hashes and public wire schemas
remain unchanged. The supported profiles remain hash64-v1/64D and
text-embedding-3-small/1536D; adapter identity drift fails before cache/provider work
and requires a separate reviewed migration.

New candidates use fixture `-v7` and semantic `-semantic-v8` suffixes. Legacy
`-v6`/`-semantic-v7` rows and graph projections remain intact, including the active
corpus until both new projections successfully activate. An explicitly authorized
reindex is required to create the new version; upgrading source alone does not
reindex or authorize paid calls. Public embedding cache keys and SQL migrations
are unchanged, so completed semantic vectors are reused by content hash/model.
A model/provider mismatch still fails runtime readiness/retrieval checks; this
change does not bypass those checks or certify new model configurations.

Evidence: the deterministic staging-path regression failed before the change
because fixture and semantic stored IDs were identical, then passed with distinct,
stable IDs and unchanged provenance. Focused tests also cover unchanged-file reuse
and unsupported model/dimension drift. The selected knowledge/provider/architecture
suite passed 53 tests with three explicit service-test skips; Ruff and formatting
passed. Checks used CPU 0/nice 15 and the existing API environment. Real PostgreSQL/Neo4j tests are added for
both switch directions, reactivation, preservation of legacy/retired rows, graph
references and cached embeddings, using synthetic provider transport. They have
not been executed in this source-only increment. No paid/model-quality claim,
service execution, image acceptance or deployment follows from these tests.
