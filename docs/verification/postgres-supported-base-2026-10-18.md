# Supported PostgreSQL base verification · 2026-10-18

This records executed candidate checks, not production acceptance. See
[ADR008](../adrs/008-supported-postgres-base.md) for rationale, provenance and
the shorter OS support period. No registry artifact was published or deployed.

## Initial complete run

[Quality39100388746](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/39100388746)
passed all six jobs for PR104 head
`5effb85e0d5448c3112a0db50ffe113ccd362de8`. The actual GitHub test merge was
`c52b29086983bb161d225c41798a234cbceca96a`; both commits have the exact same tree
`3633362816726bb08f161b83855afd39f62328de`. The candidate base was develop
`f53a953caf4b1194198c4d9cc84ac0bbfb12b9ed`, not main.

- Frozen installation, workflow validation, secret scanning, strict typing and
  740offline tests passed. Offline tests took11.05seconds.
- All41real-service tests passed in37.93seconds, including Unicode/XML/explicit
  deterministic ICU and vector operations through same-platform recovery.
- Both real applications' migrations, scoped roles, IAM/fake-provider suite,
  independent database restores and fresh-cluster restoration passed. These
  exercised the committed compatibility source, not live Google/GitHub OAuth.
- The application/container/proxy/SSE and graceful-shutdown checks passed.
- The complete candidate PostgreSQL scan passed the matching-image CLI that
  rejects every CRITICAL and fixable HIGH. This implies zero findings in those
  blocking categories; it does not assert zero unfixed HIGH or zero total findings.

The safe synthetic recovery receipt reports PostgreSQL18.6, API vector0.8.7,
UTF8/XML in both databases, explicit ICU locale `und`, a successful nearest-vector
query and no vector extension in IAM. No raw inventory, conversation, session
credential, transcript or provider report was uploaded.

The container job observed database image ID
`sha256:58015ec88c38e8567e646d8bec6346b9107a7a630529ca49266e76a0ca6fcbbd`.
This identifies that hosted runner's tested image; it is not an OCI registry
manifest or proof of byte-identical independent builds.

End-to-end run duration was222seconds. The database and container jobs took169
and174seconds respectively. These are observations from one run with its own
cache/runner state, not a measured speedup or VPS resource guarantee.

## Final evidence still required

The follow-up source exposes only bounded aggregate scanner counts through an
explicit bash/pipefail pipeline, validates the shell and output behavior with
negative fixtures, and records bounded observed database locale metadata before
and after recovery. Its exact-head complete CI result must pass independently;
the initial run cannot substitute for later revisions.

The backoffice consumes a committed, reviewed compatible revision after those
checks. Its legacy IAM recipe is not retired until vps-ops explicitly accepts
replacement ownership. Existing Debian data was never reused or chowned; this
same-platform evidence does not prove a cross-distribution data migration.
Neo4j's separate vendor-security gate, live OAuth, publication, effective VPS
headers, backup recovery and production selection remain outstanding.
