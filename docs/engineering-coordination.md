# Engineering coordination · 2026-10-17

This records application-local decisions and cross-session handoffs, not authority to
edit other repositories, promote main, publish images or deploy production.

## Ownership

| Active session | Exclusive current responsibility |
| --- | --- |
| Portfolio assistant | `portfolio-assistant-api` and `portfolio-assistant-backoffice` |
| Portfolio website | Public `portfolio`; no career-ops authority inferred from its session title |
| Pequeverso | Its store, assistant API and backoffice; confirmation recorded when received |
| VPS operations | Private `vps-ops`, Coolify, proxy and shared release/operations composition |

The four sessions were contacted through Codex task messages. Portfolio and vps-ops
confirmed their exclusive scopes. Contract changes require an identified committed
handoff; read-only references never authorize cross-repository edits. Application changes
here do not enable either assistant or execute deployment. No shared parent instructions
or global plugin configuration were changed.

## Application baseline and CI

Inspected API baseline: `efc8855` (develop before this increment). Frozen Python3.14.8,
FastAPI0.143.0, OpenAI3.29.0, LangGraph1.2.15, Pydantic2.14.1, Ruff0.17.0, mypy2.4.0,
pytest9.1.1. The vps-ops agent identified baseline commit
`1dd118469367532501d48cbb6f7fd4b9b9d6ec6e`; its committed inventory was inspected read-only.
`uv.lock`, `.python-version` and reviewed image digests remain authoritative.
This increment upgrades no runtime/tool dependency. Local uv0.12.10 can consume the lock;
CI uses pinned uv0.13.0. Maintained/stable is not automatically an LTS designation.

Observed develop/main protection requires `checks`, strict up-to-date checks and admin
enforcement. Architecture regressions run inside existing `Static and offline`; the
aggregate gate also requires real-service/container verification. Missing or failed jobs
must fail closed. No protection, coverage or required check was weakened; no additional
full build was added. Application source checks never use production secrets or paid AI.

## References and deliberate adaptations

- [Cockburn's original Ports and Adapters](https://alistair.cockburn.us/hexagonal-architecture):
  isolate application capabilities from external devices; use explicit injected ports.
- [Cosmic Python](https://www.cosmicpython.com/book/chapter_02_repository.html):
  dependency inversion and behavioral tests with replaceable adapters. Existing atomic
  PostgreSQL transactions remain authoritative; no generic repository/DI framework.
- [Microsoft architectural principles](https://learn.microsoft.com/en-us/dotnet/standard/modern-web-apps-azure-architecture/architectural-principles):
  keep application policy independent of implementation. Adopt the principle, not .NET
  project templates, classes or packages.
- [Google review guidance](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
  and [Microsoft Engineering Playbook](https://microsoft.github.io/code-with-engineering-playbook/code-reviews/):
  review design, behavior, security, tests, readability and documentation; avoid speculative
  abstractions. Local formatter/type rules in CONTRIBUTING remain canonical.

Shared principles do not mandate identical parsers, framework versions, domain models or
visual identities across products. Any dependency change needs its own compatibility
validation. Current work uses deterministic fixtures; no new paid evaluation is implied.

## Canonical physical layout closure · 2026-10-18

PR93 merged develop280b803a023fdc6d1b5631ca12c60ff12af4608b with full CI.
Concrete PostgreSQL/provider/public-source/Neo4j/observability code lives beneath
app/adapters; bootstrap owns defaults. No obsolete infrastructure facade remains.
Root ASGI/CLI commands are stable, and all nine SQL checksum resources are unchanged.
See [the accepted ADR](adrs/006-canonical-adapters.md) for actual guard behavior.

Runtime/tool versions follow [the current locked baseline](runtime-baseline.md),
not the historical initial-coordination table above. Pequeverso's later public
handoff includes PostgreSQL/Neo4j work; its earlier SQLite-only baseline is not a
current cross-project architecture claim. Product/domain packages may differ;
shared principles never imply identical services, data, secrets or implementation.

Main protection was read back on2026-10-18: required checks, strict up-to-date
verification, admin enforcement and force-push/deletion denial remain enabled.
Both application repositories use ordinary reviewed PR flows. No protection was
relaxed to merge work. [Docker ownership](docker-layout-handoff.md) preserves the
separate vps-ops/Coolify authority; merging application source cannot change its
selected image digests or authorize deployment.
