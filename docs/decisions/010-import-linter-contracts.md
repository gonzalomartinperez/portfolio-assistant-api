# ADR010: Import Linter contracts plus a residual AST guard

Status: accepted (2026-11-21, master plan task M4-4).

## Context and problem

[ADR001](001-dependency-direction.md) established six application layers and used a
hand-written AST guard to enforce their dependency direction. The guard duplicated the
import graph and layer rules of a maintained tool. It also enforced source-level rules
such as the wall-clock restriction from [ADR022](022-clock-port.md), which still need
access to Python syntax. The quality gate needs a separate check for unused code.

## Decision drivers

- Preserve the existing dependency direction, process entry points and source-level checks.
- Report violating import chains in local checks and CI.
- Verify the contracts with both accepted and rejected package trees.
- Keep dead-code findings actionable when frameworks discover handlers, validators and
  serialized fields by convention.

## Considered options

1. **Import Linter plus a residual AST guard (chosen).** Declare package constraints in
   `pyproject.toml` and keep the syntax and graph-coverage checks in the existing guard.
2. **AST guard only.** Keep the standalone checker and maintain dependency analysis
   and diagnostics in this repository.
3. **pytest-archon.** Express dependency policy in pytest. This would still require
   the source-level guard and would put import graph diagnostics inside the test suite.

## Decision outcome

This decision amends the enforcement mechanism in [ADR 001](001-dependency-direction.md).
Import Linter 2.17 checks `app` with external packages included and no ignored imports.

| Contract | Enforcement |
|---|---|
| Application layer direction | `layers` uses `app` as the container, with bootstrap above the independent presentation, adapters and AI siblings, then application and domain. `app.ai` may not import `app.adapters`. The five existing shims form an independent top tier. Each can import the six layers, and imports into or between shims are forbidden. |
| Inner layers avoid third-party and platform I/O imports | `forbidden` rejects direct imports by domain or application of the declared third-party packages and the top-level platform modules `os`, `socket`, `subprocess`, `sqlite3` and `http`. |
| Application siblings are acyclic | `acyclic_siblings` checks for dependency cycles among siblings below `app`. |

`scripts/check_architecture.py` enforces the full standard-library-only rule using
`sys.stdlib_module_names`. It checks `urllib.request` because Import Linter's graph
represents the external package as `urllib`, and domain may use `urllib.parse`. The
guard also checks imports of unclassified modules and requires `__init__.py` in
directories containing Python source and their parent packages under `app`.
Import Linter skips namespace packages and their descendants, and paths that are not
importable module names (`batch-jobs/`, `a.b.py`), so the guard rejects both. The module-level cycle
check covers self-imports and cycles between a package initializer and its descendants.

Wall-clock references and aliases, dynamic code and import calls, module classification,
`__main__` blocks and console-script targets stay in the AST guard. The clock adapter,
existing shims and documented evaluation export retain their respective exceptions.
The existing architecture test also checks for SQL text outside the database adapters
in the same four layers as before.

Vulture 2.16 scans `app` and `scripts` at 80% confidence. This catches unused imports
and unreachable code while avoiding the 60% name-based findings on framework callbacks,
Pydantic model fields and dynamically assigned adapter attributes. The exact
`ignore_names` entries cover `cls` in Pydantic classmethod validators and three type
imports referenced only in string arguments to `cast()`.

Import Linter (BSD-2-Clause; its graph library grimp is BSD-2-Clause AND BSD-2-Clause-Views AND
BSD-3-Clause, allowed in dependency review) and Vulture (MIT) are dev-group dependencies only and add
no runtime or image cost. See the [dependency plan](../master-plan/dependencies.md).

## Consequences

- `just check` and the CI static job run Import Linter and Vulture. The architecture
  tests exercise the residual guard in `just test` and CI.
- The [target state's](../master-plan/target-state.md) `independence` contract
  between adapter subpackages is deferred. The previous guard had no such rule.
- Vulture can miss unused definitions below 80% confidence. Its reports still require
  a reference search before deleting code.

## Confirmation

- Run `uv run lint-imports`, `uv run vulture` and
  `uv run python -m scripts.check_architecture`.
- Run `uv run pytest -q -p no:cacheprovider tests/architecture tests/harness tests/tooling/test_doc_links.py`.
  Isolated package probes check reversed imports, independent siblings, shim
  backedges, third-party and platform imports, `TYPE_CHECKING` imports and sibling
  cycles. A positive package exercises owned ports and shim dispatch dependencies.
  Residual probes exercise clock reads, dynamic imports, source and target
  classification, missing package initializers, non-sibling cycles and entry points.
