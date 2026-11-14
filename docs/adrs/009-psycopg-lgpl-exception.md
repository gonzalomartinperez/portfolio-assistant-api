# ADR009: Accept psycopg (LGPL-3.0-only) as a licence exception

Status: accepted (2026-11-14, master plan task M1-10, standards deviation S7).

## Context and problem

The ecosystem dependency policy allows MIT, Apache-2.0, BSD, ISC, 0BSD and BlueOak
licences for runtime dependencies (master plan `ecosystem.md` section 7). Anything
else needs a recorded exception.

`psycopg`, `psycopg-binary` and `psycopg-pool` 3.3 are licensed
**LGPL-3.0-only** (verified 2026-11-14 from the installed wheel metadata
`License-Expression` and from deps.dev). The API uses them for all PostgreSQL and
pgvector access. `langgraph-checkpoint-postgres` also depends on them directly
(`uv tree --invert --package psycopg`), so the durable run checkpointer cannot work
without psycopg.

## Considered options

1. **Keep psycopg 3 with a documented exception** (chosen).
2. Replace it with asyncpg (Apache-2.0) for application queries. psycopg would
   stay anyway, because the LangGraph checkpointer requires it, so the licence
   question would not go away and the project would carry two drivers.
3. Drop the PostgreSQL checkpointer. That would lose durable cancellation and
   resume semantics that the run lifecycle depends on.

## Decision

Keep `psycopg[binary,pool]` as an unmodified runtime library dependency.

- The application imports psycopg as a separate, dynamically loaded Python
  package. It does not copy, vendor or modify psycopg source. The application's
  own code stays MIT.
- The container image installs the unmodified wheels from PyPI, pinned by
  `uv.lock`. Their licence files stay in the installed `*.dist-info` directories.
  A recipient can replace the library inside the image (LGPL-3.0 section 4).
- `psycopg-binary` bundles native libraries in `psycopg_binary.libs/` (libpq,
  OpenSSL, Kerberos, LDAP and SASL client libraries). They carry their own
  permissive licences and are redistributed unmodified inside the wheel. They
  are covered by the existing third-party notice that the image's MIT label does
  not relicense included components.
- Never patch psycopg in-tree. A change to psycopg itself would trigger
  LGPL source-offer duties and needs a new ADR.

## Consequences

- One recorded exception to the runtime licence allow-list. Re-check it on every
  psycopg major release and whenever the image starts being published (image
  publication needs owner approval, PAA-D15).
- deps.dev OpenSSF Scorecard for `psycopg/psycopg` was 4.1 on 2026-11-14, below
  the other runtime dependencies. This is acceptable for the de facto standard
  PostgreSQL driver with an active maintainer. The weekly dependency PR keeps it
  current.
- Other non-allow-list licences seen in the locked set on the same date are
  permissive or weak-copyleft, used unmodified, and need no exception:
  `neo4j` (Apache-2.0 AND Python-2.0), `typing_extensions` (PSF-2.0), and the
  transitive MPL-2.0 packages `certifi`, `orjson` (MPL-2.0 AND (Apache-2.0 OR MIT))
  and `pathspec`. MPL-2.0 is file-level copyleft and applies only if those files
  are modified. They are listed in `docs/master-plan/dependencies.md`.

## Confirmation

- `docs/master-plan/dependencies.md` records the verified licence column
  (installed wheel metadata plus deps.dev, 2026-11-14).
- The planned supply-chain licence check (`deps-weekly` CI profile, master plan
  M1-3/M1-7) will flag any new LGPL/GPL dependency, with this ADR as the only
  allowed exception.
