# Database image verification · 2026-10-10

Application-owned images and isolated local stores under WSL Linux amd64. No
production composition, volume, deployment or publication was changed. Source is
the commit containing this report; vps-ops owns production selection and execution.

## PostgreSQL

Pinned upstream pgvector 0.8.1 image: 20 CRITICAL / 131 HIGH findings (17 critical
and 66 high fixable). The 0.8.2-tag candidate still contained PostgreSQL 17.10;
it was investigated but not retained. The verified 0.8.7-pg17 manifest contains
stable PostgreSQL 17.11 and pgvector 0.8.7. Its base still had 16 CRITICAL / 106
HIGH findings (13 critical and 41 high fixable).

Dockerfile.postgres derives from that immutable upstream digest, applies available
stable-distribution security updates, removes unnecessary gosu and runs as postgres
UID/GID 999. The official entrypoint skips root ownership repair in this mode.
A package inventory remains at /usr/share/assistant-postgres-packages.txt. Apt
repositories are mutable: rebuilds are not claimed bit-identical; promote only the
actual tested immutable digest, retaining its package inventory and scan. Never
rebuild application/database sources on the VPS as normal release deployment.

Final local image ID:
`sha256:cb07f2c5ce8ed9deb049235e8806f1a90d4ebabdf99a094647436ab07b21a16b`.
Size: **175,498,570 bytes**. Full scan: 3 CRITICAL / 65 HIGH / 173 MEDIUM / 164 LOW /
7 UNKNOWN, **no fixable findings** in this scanner database. The remaining critical
findings concern libsqlite3, libxml2 and zlib source packages. No ignore file,
manual scanner override or production risk waiver was added. Assess actual runtime
reachability and upstream fixes before production; this is not a clean-image claim.

Local Compose uses a read-only root filesystem, dropped capabilities, no-new-privileges,
bounded writable tmpfs for /tmp and /var/run/postgresql, and its existing persistent
PGDATA volume. Fresh-volume initialization, readiness, CREATE EXTENSION vector and
UID 999 were exercised. Restricted privileges and sockets remained functional.
CI builds this PostgreSQL image once, starts only its owned fixture and records its
actual container ID for evaluation guards. It scans the complete image and rejects
fixable critical/high findings; all unfixed findings stay in retained artifacts.
The API image's stricter gate still rejects every CRITICAL finding. Neither gate
is production approval. Stable security-package installation is intentionally fresh
on hosted runners, while the existing API BuildKit and uv caches are preserved.

## Isolated cold-copy compatibility

Stopped, owned `portfolio-runtime-20261010` volumes were mounted read-only and copied
into new `assistant-upgrade-overnight-20261010` volumes. Original stores were not
modified. The old-Neo4j baseline startup did not complete before replacement, so
this is not a baseline-versus-upgrade performance or full restoration proof.
The copied graph subsequently opened with Neo4j 5.26.31 and contained 214 nodes /
752 relationships. PostgreSQL's intermediate 17.10/extension 0.8.1 inventory had
91 chunks / 10 knowledge versions. Replacement with 17.11 and explicit owner SQL
`ALTER EXTENSION vector UPDATE TO '0.8.7'` preserved these counts and graph counts.
The final non-root PostgreSQL image also opened the copied store unchanged.

**291 tests passed in 25.90 seconds**, including 25 real PostgreSQL/Neo4j cases,
with the final images and existing application boundaries. New provenance guard
cases cover the custom database image; declaring a repository label does not prove
absence of prior data or grant authority to use someone else's services. A separate
fresh PostgreSQL project initialized extension 0.8.7 under the hardened settings.
Raw scans and inventories are ignored in artifacts/security-20261010/. No private
conversation or key is committed as evidence. Counts do not prove backup completeness.

## Neo4j

Complete OS/Java scan of the pinned 5.26.31 image: 1 CRITICAL / 113 HIGH / 869 MEDIUM /
240 LOW / 6 UNKNOWN. Nine high Java findings have listed fixed versions. The critical
finding is reported against linux-libc-dev headers; this is not a finding that the
container runs a Linux kernel of that version. Runtime applicability and the host
kernel must be assessed separately. Jackson jars belong to the vendor distribution:
do not independently replace them or suppress scanner findings. A compatible vendor
patch/digest and its store compatibility remain a release-selection gate.

The first full Java scan timed out while provisioning its database; a second scan
with a bounded 10-minute timeout completed using the downloaded cache. No packages
were omitted. Hosted PR CI does not download this ~936 MiB Java database on every
run; the full vendor scan is recorded for release assessment. Future release
selection must rescan the chosen digest with current advisory data.

References: [PostgreSQL support/upgrade policy](https://www.postgresql.org/support/versioning/),
[pgvector 0.8.7 fixes](https://github.com/pgvector/pgvector/blob/v0.8.7/CHANGELOG.md),
[Neo4j minor upgrades](https://neo4j.com/docs/upgrade-migration-guide/current/version-5/upgrade-minor/).
