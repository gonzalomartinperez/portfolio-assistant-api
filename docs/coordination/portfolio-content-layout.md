# Public content layout compatibility

The portfolio's committed candidate
[`12e68c662b855422411ffdfd1d5334f6b4b0e086`](https://github.com/gonzalomartinperez/portfolio/commit/12e68c662b855422411ffdfd1d5334f6b4b0e086)
moves the eight professional profile files from `src/content/{en,es}/` to
`content/{en,es}/`. The reviewed topics remain `profile.ts`, `experience.ts`,
`projects.ts` and `education.ts`. This compatibility increment adds no other public
source, document parser, provider, service or paid evaluation.

The allowlist and optional structured projection accept both exact layouts.
Sibling/private files, backup extensions and arbitrary `content/**` paths remain
excluded. Two paths representing the same locale/topic in one committed tree are
rejected before indexing, rather than mixing competing profile versions.

Domain ranking, locale fallback, starter questions and parameterized graph queries
apply the same language rules to both layouts. Physical source paths remain intact
in stored records and GitHub citations. A new root path therefore produces a new
source identity; an older answer's immutable commit/path/line citation stays valid.
Only the active corpus contributes to new retrieval. Retired PostgreSQL and Neo4j
projections are preserved, not merged into current results.

## Index format and rollout

The new source format uses fixture `-v8` and semantic `-semantic-v9` corpus suffixes.
Changing the format is necessary even for the same Git commit: an older indexer
could already have activated an incomplete README-only index for a root-layout tree.
The new worker cannot reuse that version as an unchanged successful publication.
API readiness, retrieval and starter reads reject the previous format until an
appropriate index has been activated. Query embeddings are not requested on that
rejected path. No database migration or public HTTP/SSE field change is needed;
`contracts/knowledge.schema.json` expands its approved source-path pattern.

Coordinate API and knowledge-worker versions in vps-ops. Build/select their shared
root-aware application image, authorize indexing with the configured embedding
profile, verify both projections and only then admit traffic. The continuously
running worker still resolves the approved public `main` branch to immutable
commits; it does not read another agent's working tree. Publication remains guarded
against superseded observations, and freshness cannot disguise an unsupported index.
Retain the producer's disabled assistant flag and existing production approval gates.

Existing matching public semantic vectors may be reused; missing vectors still
require paid authority and the existing ledger budget. Fixture vectors are 64-dimensional
hashes and do not establish production semantic quality or 1536-dimensional capacity.
Rollback after the producer moves must retain a root-aware API/worker pair; reverting
to the pre-transition reader is not a safe automatic rollback. Preserve old snapshots
and coordinate any explicit corpus reactivation instead of deleting or rewriting them.

## Verification

The initial seven-case regression run reproduced four failures: the root manifest
contained only README, starters disappeared, projection validation rejected paths and
retrieval returned no professional sources. The legacy-layout cases passed.
The implementation adds tests for profile-format invalidation before embedding I/O,
both layouts, locale isolation, citations and ambiguous-path rejection.

Run `uv run pytest -q tests/test_content_root_compatibility.py tests/test_index_identity.py`.
The real-service cases are `tests/test_content_root_integration.py` and
`tests/test_index_identity_integration.py`: use the documented isolated PostgreSQL/Neo4j
fixture and explicit `TEST_INTEGRATION=1`. They exercise the actual worker publication
adapter, repeated polling, path relocation, changed content, reuse, both graph language
filters, version retirement and supporting citation spans. Synthetic provider transport
is not a real OpenAI embedding or model call.

The ordinary CI retrieval corpus remains pinned to its historical public commit for
repeatability. Also index the exact reviewed producer candidate with fixture embeddings
before accepting the coordinated cutover; a synthetic move alone does not establish
that the producer's actual files were consumed. Record source/index/image revisions,
both-store results and remaining limitations in the integration handoff.

The executed fixture cutover uses API source
`b53cd1998e17c27a7b6ba17ac2317d9db6cfcfce` and the exact producer above. It
consumed all eight relocated professional files, validated both projections and
both locales, preserved retired versions and passed 20 HTTP turns. See the
[dated acceptance evidence](../verification/graph-readiness-2026-10-18.md#executed-counterfactual)
for counts, receipt hashes, original failed attempts and environment limitations.
No generation/embedding provider call or portfolio activation is implied.
