# Canonical API adapter layout: verification

The implementation builds on develop5499cf467d05e4328eaa2f51caddd14a0e266b88
and the RED preflight754a9bf951f1174c45a69d2725ce3644c0e94cc3. Concrete
I/O now lives in capability packages under app/adapters. Bootstrap owns defaults;
no adapter imports bootstrap. The obsolete app.infrastructure namespace is gone.

Current consumers in app, scripts, tests and contract export were inspected and
migrated. Five root ASGI/CLI entry points remain stable. There is no identified
deployed external importer requiring compatibility facades. Historical receipts
still describe their original revisions; no evidence has been relabeled.

## Local commands actually executed

- `.venv/bin/pytest -q -m 'not integration'`:671passed,37deselected,42.35s.
  The retired positive facade-exception case is removed; negative obsolete-module
  probes and stable root command dispatch remain. No integration test was skipped
  by changing its marker or weakening an assertion.
- `.venv/bin/pytest -q tests/test_architecture.py tests/test_adapter_layout.py`:
  34passed,6.05s. Includes missing SQL resources, nine original SQL checksums,
  inward backedges, unclassified nested modules and actual CLI forwarding.
- `.venv/bin/mypy`:36strict inner-layer modules pass; this is not a claim that
  every outer persistence module is strictly typed.
- `.venv/bin/python -m contracts.export`: wire artifacts unchanged; only the
  exporter's implementation import changes.
- Ruff lint/format, architecture command and portable skill validation pass.

The earlier complete run found stale security-test paths and skill links; both
were corrected to canonical modules, preserving the SDK retry/base-URL assertions.
No dependency, SQL bytes, endpoint, cookie, generation policy or provider changes.
A test fresh-module namespace fix removes a runpy pre-import warning without
suppressing warnings.

Real PostgreSQL/Neo4j, hardened production image and hosted checks must pass on the
implementation PR before merge. No local heavy services ran during this increment.
Production deployment/publication, live model calls and the outstanding vendor
Neo4j image acceptance remain held. Folder alignment does not close those gates.
