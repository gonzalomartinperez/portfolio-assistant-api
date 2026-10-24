# Research: file index, code standard, docs, community files and skills

Planning research only. The current canonical standard remains
[CONTRIBUTING.md](../../../CONTRIBUTING.md); nothing here changes it until a later
authorized task does.

## Master file index (current → target)

| Current | Target | Note |
|---|---|---|
| `app/ai/retrieval.py` | `app/ai/retrieval/{__init__,query_analysis,candidates,fusion,rules,selection}.py` + `rules.toml` | A1 |
| `app/ai/workflow.py` | `app/ai/workflow/{graph,state,nodes}.py` | A4 |
| inline prompt in `app/adapters/providers/answer.py` | `app/ai/prompts/{answer,judge}.vN.md` + `registry.py` | A3 |
| `app/adapters/providers/voice.py` | `app/ai/prompts/voice.{en,es}.md` | it is prompt content |
| `app/domain/fixture.py` | `app/adapters/providers/fixture_answer.py` | A2 |
| format regexes in `app/domain/evidence.py` | `app/adapters/portfolio/structured.py` | A2 |
| `app/adapters/retrieval.py` | `app/adapters/postgres/knowledge_index.py` (+ graph in `adapters/neo4j/`) | one adapter per technology |
| `app/{main,migrate,retention,knowledge_sync,knowledge_watch}.py` | `app/bootstrap/cli/*.py` + `[project.scripts]` | A8 |
| `app/presentation/http.py` (369 LOC, high CC) | `app/presentation/routes/{session,conversations,runs,knowledge,feedback,analytics,health}.py` | one router per resource |
| `app/presentation/middleware.py` `error()` | `app/presentation/errors.py` + `messages.py` (EN/ES) | A6 |
| `tests/test_*.py` (52 flat files) | `tests/{unit,integration,contract,e2e,property,security,eval}/…` | see [testing](testing.md) |
| `evals/*-2026-10-1x.json` (13 dated artifacts) | `evals/{retrieval,assistant,conversations,voice,web}/` + `evals/results/<date>/` | separate cases from results |
| `docs/verification/*` (46) | `docs/evidence/2026-10/…` + index | historical archive |
| `docs/*.md` (34) | Diátaxis (below) | |
| `IMPLEMENTATION_STATUS.md`, `docs/work-checklist.md`, `docs/quality-pass.md` | `CHANGELOG.md` + `docs/explanation/status.md` (one living page) | |
| `docs/decisions.md` | absorbed into MADR ADRs | |
| `scripts/check_architecture.py` | `tools/architecture.py` (or it stays) | repository scripts vs. application scripts |
| — | `CHANGELOG.md`, `CODEOWNERS`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, `.github/ISSUE_TEMPLATE/{bug,feature,eval-regression}.yml`, `config.yml`, `justfile`, `.pre-commit-config.yaml`, `.devcontainer/` | community files below |

## Python code standard

Base: the **Google Python Style Guide** (already declared in `CONTRIBUTING.md`) on top
of **PEP 8**, with Ruff as formatter and linter. Explicit and justified deviations:

| Topic | Google | Decision here | Reason |
|---|---|---|---|
| Formatter / line | yapf/pyink, 80 | Ruff format, 88 | ecosystem, no debate |
| Quotes | consistent | single (already configured) | keep; changing it is churn without value |
| Imports | modules, not names | names from internal modules and typing are allowed | readability with `Protocol` ports |
| Docstrings | Google | Google (pydocstyle `google`), mandatory only for public API and ports | avoid narration |
| Linter | pylint | Ruff (`PL` subset) | speed |
| Typing | recommended | **mandatory**, mypy `--strict` across `app/` and `scripts/` | target 95 |
| Exceptions | specific | same; broad only at fault boundaries with `# noqa: BLE001` + reason | already in CONTRIBUTING |

Target Ruff configuration (ratchet with `per-file-ignores` that only shrink):

```toml
[tool.ruff]
target-version = "py314"
line-length = 88

[tool.ruff.lint]
select = ["E","W","F","I","N","UP","B","S","ASYNC","BLE","C4","C90","D","DTZ","ERA",
          "FBT","G","LOG","PERF","PIE","PL","PT","PTH","RET","RSE","RUF","SIM","T20","TRY",
          "ANN","TC"]
ignore = ["D1",      # docstrings mandatory only through review of the public API
          "TRY003",  # short messages in domain exceptions are acceptable
          "PLR2004"] # reviewed case by case; too much noise at contract limits
[tool.ruff.lint.mccabe]
max-complexity = 10
[tool.ruff.lint.pylint]
max-args = 6
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101","ANN","PLR2004","D"]
"scripts/**" = ["T20","S603","S607"]
[tool.ruff.lint.pydocstyle]
convention = "google"
```

mypy: `strict = true`, `files = ["app", "scripts", "contracts"]`,
`warn_unreachable = true`, plugin `pydantic.mypy`. Evaluate `ty`/`pyright` as a second
checker only as an experiment.

## Docs set

- **README as a showcase** (target structure, ≤ 250 lines):
  1. Hero (one sentence) + a short GIF/MP4 of streaming with citations.
  2. "Why it's interesting": 5 engineering bullets linking to evidence (bilingual hybrid
     GraphRAG, cancellable streaming, atomic cost budget, versioned contracts,
     architecture with a guard).
  3. **Measured results** (table): Recall@5 EN/ES, citation support, abstention, TTFT
     p50/p95, cost per answer, mutation score, coverage, with date and commit.
  4. Quickstart: `just demo` (one command, ephemeral ports, fixture).
  5. Architecture: C4 level 1 (context) and 2 (containers) in Mermaid + link to level 3.
  6. "Status & limits": **one** paragraph with what is in "Current state" today + link.
  7. Diátaxis docs map, license.
- **Diátaxis:** `docs/tutorials/` (first local run, first eval), `docs/how-to/`
  (knowledge sync, change a prompt, run authorized live evals, rotate the corpus, CVE
  triage), `docs/reference/` (API, SSE, env vars, config, metrics, CLI),
  `docs/explanation/` (architecture, retrieval, evaluation, privacy, threat model,
  costs), `docs/adr/` (MADR 4.0 with `status/date/deciders` front matter),
  `docs/evidence/` (dated history, read-only).
- **C4:** Structurizr DSL or Mermaid C4 in `docs/explanation/architecture.md`;
  regenerate the SVG in CI if DSL is used.
- **CHANGELOG** (Keep a Changelog, generated by release-please), **CONTRIBUTING**
  (exists; add `just` tasks and the test layout), **SECURITY** (exists; add the SLA from
  the ADR-018 policy).

## GitHub community files

`CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `CODEOWNERS`
(`* @gonzalomartinperez`), `SUPPORT.md`, YAML issue forms (bug, feature,
eval-regression with corpus/prompt version fields), `ISSUE_TEMPLATE/config.yml`
(disable blank issues, link to security advisories), PR template (exists; add "eval
impact" and "contract impact" checklist items), repository topics (exist), repository
**homepage** (empty today → link to the portfolio), social preview image, Releases.

## Agent skills: audit and proposal

State [read]: 5 skills in `.claude/skills/` with symlinks in `.agents/skills/` (Codex);
validated by `scripts/validate_skills.py` and scenarios in
`tests/fixtures/skill_scenarios.json`.

| Skill | LOC | Strength | Problem | Action |
|---|---|---|---|---|
| `api-change-storage` | 41 | precise scope | — | keep |
| `api-change-stream` | 39 | "Use for X, not Y" | does not cite the SSE schema as a checklist | add a contract checklist |
| `api-change-use-case` | 62 | good | repeats authority boilerplate | extract to `AGENTS.md` |
| `api-maintain-knowledge` | 103 | complete | dense prose, mixes 8 subtasks and references to dated reports | split: SKILL.md ≤ 60 lines + `references/{web-context,layout,readiness}.md` |
| `api-verify-release` | 191 | exhaustive | too long for progressive disclosure; no helper scripts | SKILL.md ≤ 80 + `references/` + `scripts/select_checks.py` |

New skills (aligned with the plan):

- **`api-evaluate-quality`**: run the offline regression/retrieval suites, compare
  against the baseline, report Recall@5/nDCG per locale and (with authorization) a
  capability sample; includes judge calibration. *Use for measuring quality; not for
  changing retrieval code.*
- **`api-change-prompt`**: edit a versioned prompt, bump the `PromptSpec`, run
  regression + eval diff, update the prompt changelog.
- **`api-triage-security`**: read Trivy/CodeQL/osv reports, classify, draft a VEX
  statement or an issue with an SLA, without modifying vendor images.
- **`api-write-adr`**: a MADR 4.0 template with numbering and links.

Validate each skill with positive and negative scenarios in `skill_scenarios.json` (the
mechanism already exists) [source: anthropics/skills, skill-creator].
