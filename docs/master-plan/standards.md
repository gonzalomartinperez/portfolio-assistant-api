# Standards

Applies ecosystem section 10.2 (Python) and 10.3 (enforcement). Source: [10](research/10-standards-dependencies.md), [02](research/02-python-architecture.md). Deviations from the ecosystem or from the repo's current rules are listed explicitly.

## 1. Style guide choice

| Topic | Choice | Why |
|---|---|---|
| Language semantics | Google Python Style Guide, adapted to Python 3.14 and typed contracts (already the repo reference in CONTRIBUTING.md) | It is the repo's existing convention; ruff encodes most of it, so enforcement is automatic |
| Formatting | `ruff format`, line length 100, double quotes | Ecosystem 10.2. **Deviation removed:** the repo uses single quotes and 88 columns today; one mechanical formatting PR (M3) aligns it |
| Lint | Ruff families `E W F I B C4 UP SIM RUF PERF PIE PT PTH TC ASYNC S T20 TRY ARG FAST LOG G DTZ ERA FURB N RET D ANN`; ignore `E501 TRY003 D203 D213`; tests ignore `S101 ANN D ARG` | Ecosystem 10.2; never `ALL`. Today the repo selects a handful of families; the gap is measured in audit.md (1,349 findings with the sibling ruleset, 1,085 of them test asserts) |
| Docstrings | Google convention on public contracts and operationally sensitive methods (invariants, ownership, cancellation, failure behaviour, units); no restating of annotations | Kept from CONTRIBUTING; `D` enforces shape, review checks content |
| Types | `mypy --strict` over all of `src/` as the gate; Pyrefly or pyright strict as a non-blocking second job | Ecosystem 10.2. Baseline 199 errors, scope 39/95 files |
| Complexity | At most 10 per function, ratcheted per file (11 functions above today, max 48) | Ecosystem 10.2 and rubric D2 |
| Imports | Absolute imports, explicit names; relative imports allowed inside a package; no wildcard; isort by ruff | Ecosystem deviations from the Google guide |
| Naming | `snake_case` modules and functions, `PascalCase` classes, kebab-case only for non-Python files that are not framework-mandated; tests `test_<unit>.py` in the lane directory | Python convention |
| Data objects | Frozen dataclasses for inner value objects, pydantic at transport and configuration boundaries, `Protocol` for ports | Existing rule, kept |
| Errors | Catch specific exceptions; broad catches only at public fault boundaries with a local explanation; never swallow cancellation; never put provider or DB exception text in responses; RFC 9457 problem documents | Existing rule plus ecosystem 10.2 |
| Time and randomness | Clock port; no `datetime.now()` outside it; seeds explicit in tests and evals | Ecosystem 10.2; guard rule |
| Logging | structlog-style JSON through the existing logging bootstrap; no visitor text; request id on every line | Ecosystem 17 |
| Prompts | Files with front matter and a lock hash; English prompt text, Spanish only in the language-specific voice fragments | [assistant-quality.md](assistant-quality.md) section 10 |
| Commits and branches | Conventional Commits (PR title checked), `feat/ fix/ chore/ docs/ deps/` branches, merge commit into develop (PR title as Conventional Commit) | Ecosystem 3.1 |
| Language policy | English for code, docs, comments, commits; neutral Latin American Spanish for user-facing assistant behaviour and static Spanish strings; owner name written exactly "Gonzalo Martin Perez" in both languages | AGENTS.md and ecosystem 14.2 |

## 2. Explicit deviations from the ecosystem

| # | Deviation | Reason | Revisit |
|---|---|---|---|
| S1 | Layer names `ai` and `presentation` kept, ports under `application/ports/` (PAA-D21) | Churn without behaviour change; guard already encodes the rule | If the sibling API renames, align both in one PR |
| S2 | Settings keep `extra="ignore"` (dotenv source), unknown keys caught by a schema test | `extra="forbid"` rejects unrelated dotenv entries | pydantic-settings behaviour change |
| S3 | Provider-port cassettes instead of HTTP cassettes (PAA-D6) | Weekly SDK bumps would invalidate HTTP recordings | Sibling standardizes on `vcrpy` |
| S4 | Golden tier has no sealed holdout; holdout lives in the full tier (PAA-D16) | Regression items must be readable by whoever fixes them | none |
| S5 | No LangSmith dataset mirror, tracing stays off (PAA-D8) | Privacy decision encoded in settings validation | Phase V, if the owner wants hosted viewing of synthetic eval runs only |
| S6 | Test mix target 45% integration by M6 instead of 60% (testing.md T1) | Evals and pure domain tests are large and cheap | M6 review |
| S7 | `psycopg` (LGPL-3.0) is a runtime dependency outside the licence allow-list | Required by `langgraph-checkpoint-postgres`; dynamic use as a library, unmodified | Recorded in [ADR009](../adrs/009-psycopg-lgpl-exception.md) (M1-10); re-check on each major |

## 3. Enforcement

| Mechanism | Detail |
|---|---|
| One command | `just check` equals the CI static job and the pre-commit hook: `ruff check`, `ruff format --check`, `mypy`, `lint-imports`, `scripts/check_architecture.py`, `vulture`, docs checks, skills validator |
| AGENTS.md match | `tests/harness/test_agents_commands.py` extracts backticked commands from AGENTS.md and checks them against `justfile` and `pyproject.toml` |
| Ratchets | `scorecard/ratchets/static.json` holds mypy errors, ruff findings per rule, complexity offenders, vulture count: they only decrease |
| Suppressions | No blanket suppression; a local `# noqa` or `# type: ignore` needs a rule code, a reason and an issue link; a test counts them and the count only decreases |
| Rule changes | Need an ADR and bump of the ecosystem version; no repo edits its own `ecosystem.md` |
