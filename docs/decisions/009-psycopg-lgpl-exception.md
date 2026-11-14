# ADR009: Accept psycopg (LGPL-3.0-only) as a licence exception

Status: accepted (2026-11-14, master plan task M1-10; the exception was
pre-approved as standards deviation S7 in the owner-approved master plan).

## Context and problem

The ecosystem dependency policy allows MIT, Apache-2.0, BSD, ISC, 0BSD and BlueOak
licences for runtime dependencies (master plan `ecosystem.md` section 7). Anything
else needs a recorded exception.

`psycopg`, `psycopg-binary` and `psycopg-pool` 3.3 are licensed
**LGPL-3.0-only** (verified 2026-11-14 from the installed wheel metadata
`License-Expression` and from deps.dev). The API uses them for all PostgreSQL and
pgvector access. `langgraph-checkpoint-postgres` also requires `psycopg` and
`psycopg-pool` (`uv tree --invert --package psycopg`), so the durable run
checkpointer cannot work without them.

This ADR records an engineering policy decision, not legal advice.

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
- `psycopg-binary` bundles native libraries in `psycopg_binary.libs/`: libpq,
  OpenSSL (libssl, libcrypto), Kerberos (libkrb5, libk5crypto, libkrb5support,
  libgssapi_krb5, libcom_err), OpenLDAP (libldap, liblber), Cyrus SASL, libpcre,
  libselinux, libkeyutils and libcrypt. They carry separate third-party licences,
  mostly permissive; at least libkeyutils and libcrypt are LGPL-2.1-or-later. They
  are shipped unmodified inside the wheel and are covered by the existing notice
  that the image's MIT label does not relicense included components. The wheel's
  embedded SBOM (`auditwheel.cdx.json`) shows they come from an older
  manylinux base; the M4 dependency review re-checks this.
- `[binary]` is used because the slim runtime image has no compiler or system
  libpq. Switching to `psycopg[c]` with the Debian libpq package would remove the
  bundled copies; that is an option for the M1-4 image work, not a requirement.
- Never patch psycopg in-tree. A modified psycopg would likely bring LGPL
  source-offer duties once the image is conveyed to anyone (it is not published
  today, PAA-D15), so it needs a new ADR first.

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
- If the image is ever distributed, ship the GPL-3.0 text next to the LGPL-3.0
  text (LGPL-3.0 section 4) together with the bundled-library notices.

## Confirmation

- `docs/master-plan/dependencies.md` records the verified licence column
  (installed wheel metadata plus deps.dev, 2026-11-14).
- The planned supply-chain licence check (`deps-weekly` CI profile, master plan
  M1-3/M1-7) will flag any new LGPL/GPL dependency, with this ADR as the only
  allowed exception.
