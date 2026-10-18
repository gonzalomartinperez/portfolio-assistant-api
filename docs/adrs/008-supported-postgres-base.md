# ADR008: Evaluate a maintained PostgreSQL base without the Debian libxml2 blocker

Status: candidate; complete exact-image verification and independent review required.

## Context

The backoffice's complete IAM image scan exposed CVE-2026-6653 in Debian libxml2.
The [Debian assessment](https://security-tracker.debian.org/tracker/CVE-2026-6653)
currently marks both supported Debian variants vulnerable. Changing the index pin,
switching between those Debian variants or suppressing unfixed findings is not a fix.

Production needs one vector-capable PostgreSQL engine per project, with separate
assistant/IAM databases and privileges. A second IAM-only replacement would leave
the common artifact unresolved. Production selection belongs to private vps-ops.

## Candidate

Keep PostgreSQL18.6 and pgvector0.8.7. Use the official PostgreSQL18.6 Alpine3.24
image, pinned by immutable index, and build the checksum-verified pgvector release
in a separate stage with `OPTFLAGS=""`. Preserve XML, ICU, the official entrypoint
and all existing bootstrap/HBA resource bytes. Builder dependencies stay outside
the runtime; copy pgvector's license and build-package inventory with the extension.
Pin direct compiler packages and the stable-branch libxml2 patch. Native APK
signature verification remains enabled; no unstable repository or vendor fork.

The supported test target remains linux/amd64. The official source is
[e00e1bd3](https://github.com/docker-library/postgres/blob/e00e1bd34ec5c8a8e7ad89b273b3d42efaf6d5bc/18/alpine3.24/Dockerfile).
Registry metadata inspected2026-10-18 resolves index
`sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873`
to amd64 manifest
`sha256:d8703cd7fba306b9fec9268ecedfa8a966846c053036a60e3635791957eb2f66`.
Neither source inspection nor a version number proves that the final image is clean.

## Compatibility and acceptance

Alpine uses musl and UID/GID70. A separate local volume name prevents silently
mounting Debian-owned PGDATA. Never chown/reuse an old data directory as a migration.
Existing data requires a separately rehearsed logical export/restore, privileges,
locale/collation and index review. A same-image fresh-cluster restore does not prove
cross-distribution migration or rollback compatibility.

Required evidence includes full current image inventory with every CRITICAL and
fixable HIGH rejected, portable vector compilation, actual vector queries, UTF8/XML
and explicit deterministic ICU checks, both applications' migrations and restricted
roles, independent logical restoration/restart and the unchanged API/browser suite.
Unfixed HIGH findings remain explicit production-assessment requirements.

The application image, public API/SSE contract, migrations and Neo4j baseline do not
change. No publication, deployment, production pin or backoffice legacy-recipe
retirement follows from this ADR. The backoffice consumes a committed API handoff
only after the candidate passes. vps-ops must explicitly accept replacement
ownership before the legacy IAM recipe is retired.
