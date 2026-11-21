# Decision records

Architecture decision records (ADRs) for the portfolio assistant API, one file per decision named `NNN-title.md`.
Paths are stable: new ADRs are added here and existing files do not move. New records follow MADR 4 (see the
`write-adr` repository skill). Superseding records link both ways.

Numbers are never reused. Gaps: ADR 007 was never written, and numbers 010, 015, 018 and 020 are not present in
this tree. The dated decision log that preceded the ADRs is archived at
[decisions-log-2026-09.md](../evidence/archive/2026-10/decisions-log-2026-09.md).

| No. | Title | Status |
|---|---|---|
| 001 | [application policies own their boundaries](001-dependency-direction.md) | Accepted 2026-09-27 |
| 002 | [shared KVM 4 VPS and one assistant origin](002-shared-kvm4-origin.md) | Accepted 2026-09-27; production ownership superseded by ADR 003 |
| 003 | [production ownership and Coolify](003-production-ownership.md) | Accepted |
| 004 | [current public knowledge and one OpenAI generation model](004-current-public-knowledge.md) | Accepted implementation direction; paid evaluation and production pending |
| 005 | [proposed PostgreSQL consolidation within Portfolio](005-project-postgres-consolidation.md) | Application implementation verified locally; production adoption pending |
| 006 | [Canonical adapters and explicit operator composition](006-canonical-adapters.md) | Accepted (merged through PR93) |
| 008 | [Evaluate a maintained PostgreSQL base without the Debian libxml2 blocker](008-supported-postgres-base.md) | Candidate; exact-image verification and independent review required |
| 009 | [Accept psycopg (LGPL-3.0-only) as a licence exception](009-psycopg-lgpl-exception.md) | Accepted |
| 011 | [In-repo eval harness package with deterministic graders](011-eval-harness.md) | Accepted |
| 012 | [Compare evidence by layout-neutral canonical keys](012-layout-neutral-evidence-keys.md) | Accepted |
| 013 | [Provider-port cassettes for the golden lane](013-provider-port-cassettes.md) | Accepted |
| 014 | [Prompt registry in git with a lock file](014-prompt-registry.md) | Accepted |
| 016 | [Frozen in-repo snapshot of the approved public corpus](016-frozen-public-corpus-snapshot.md) | Accepted |
| 017 | [Canonical API image with `api` and `worker` targets](017-canonical-api-image.md) | Accepted |
| 019 | [One grouped dependency PR per week, merged manually](019-weekly-dependency-pr.md) | Accepted |
| 021 | [External tracing stays off; no hosted prompt or dataset registry](021-tracing-off-no-hosted-prompt-registry.md) | Accepted |
| 022 | [Clock port for wall-clock time](022-clock-port.md) | Accepted |
| 023 | [Scoped mutation testing with mutmut on Python 3.14](023-mutation-testing-mutmut.md) | Accepted |
| 024 | [Load budgets and baseline ratchet](024-load-budgets-baseline.md) | Accepted |
