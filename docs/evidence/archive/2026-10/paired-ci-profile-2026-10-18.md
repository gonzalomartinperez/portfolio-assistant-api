# Paired API CI profile candidate

This increment follows the owner-coordinated profile revision
eb8288349f797d1fd5d51bfc349e70da8eaf3c01 without accessing that private repository
from public CI. It builds on Docker candidatea589cc1, merged through PR94 as
cf3b68be8ddd45460d8156ac73d6eaf175e04d99. That earlier full run39091552603 passed
676offline and37real-service tests; static36s, services/image251s, aggregate4s.
It is a baseline, not evidence for the new job graph.

## Coverage map

| Job | Retained substantive work | Evidence transport |
| --- | --- | --- |
| workflows | Reviewed actionlint download/checksum and every active workflow | Safe Actions diagnostics |
| secrets | Full reachable history plus worktree credential patterns | Detector/path metadata only |
| static | Frozen install, licensing/skills, format/lint/mypy, bilingual bank, offline/contract/architecture/CI negatives and contract drift | Safe Actions logs; no image archive |
| database | Own PostgreSQL/Neo4j, explicit migrations, pinned corpus, complete integration selection, bilingual evaluation, two-app scoped identities and recovery | Bounded synthetic project-database receipt only |
| container | Own PostgreSQL/Neo4j/corpus, application image, PG/app/full optional Neo4j assessment, non-root streams, active SIGTERM and local proxy | Run/source/workflow/config hashes and inspected local IDs; no image publication |
| checks | Every five expected job outcomes, always evaluated | Required checks context; actual identity must be verified remotely |

Independent database/container fixtures are intentional. No live database crosses
runner boundaries. Only the static uv job writes the shared dependency cache;
others restore frozen inputs. Full history is fetched only by the actual secret
scan. The API image is built once in the container job and reused there. No public
image transport, private credentials or broader token permissions are added.

## Local verification

The complete offline suite passed691tests,37real-service cases excluded,14.03s.
The focused profile/layout/vendor/policy/release suite passed91tests,1.70s before
two additional clean-input fail-closed cases. Ruff, strict mypy36inner modules,
contract drift and actionlint passed. An independent code-only review found no
P1/P2; it did not execute hosted checks or certify remote protections.

The actual aggregate shell is exercised with each prerequisite failed, cancelled,
skipped, pending, empty or missing. Missing jobs/renamed IDs, graph changes, path
filters, elevated permissions, moving action tags and hidden failures are rejected.
Source identity rejects another candidate, malformed run/workflow/base metadata and
dirty/unverifiable build inputs without printing a diff or environment values.

Hosted acceptance, precise runtime cost/cache behavior and the required-context
transition remain pending until this exact implementation PR passes. First require
both old and new contexts, read back enforcement, then retire only the old context;
never open a protection gap. Post-merge develop/main runs identify their actual
commits. Source merging/tagging remains distinct from blocked Neo4j production
acceptance, image publication, live OAuth and deployment.
