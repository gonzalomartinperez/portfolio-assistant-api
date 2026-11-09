# Skills and agentic harness

Applies ecosystem sections 15.1 to 15.6 and 15A. Research: [08](research/08-docs-readme-skills.md) section 4, [14](research/14-codex-harness.md) (Codex), [15](research/15-claude-code-harness.md) (Claude Code). Goal: the owner does not need to review code; the harness makes every PR carry its own evidence.

## 1. Audit of the existing skills (5, at `origin/develop`)

| Skill | Lines | Job | Findings | Destination in the standard catalog (15.5) |
|---|---|---|---|---|
| `api-change-use-case` | 62 | Application rules, ownership, limits | Good scope, one job | Stays as a repo-specific skill; add pointer to import-linter and mutation scope; add evals |
| `api-change-stream` | 39 | Provider and LangGraph lifecycle, SSE contract | Short, one job | Stays; add oasdiff, SSE conformance and cancel tests to its checklist; add evals |
| `api-change-storage` | 41 | Migrations, transactions, accounting, recovery | One job | Stays; add expand/contract, forward-only and grants tests; add evals |
| `api-maintain-knowledge` | 103 | Bilingual retrieval, graph, grounding, indexing | Mixes ingestion, retrieval evaluation and graph in one body | Ingestion and provenance stay here; evaluation content lands in `evaluate-assistant`; retrieval changes point at the ablation harness |
| `api-verify-release` | 191 | Verify a change, CI, containers, release evidence, security review | Over the 120-line catalog limit; three jobs in one | Content lands in `verify-release` (release profile, changelog, tags, post-deploy), `implement-task` (select and read checks) and `review-change` (security review delegates to `owasp-security-review`); the file is then removed (nothing deleted before its content lands) |

Catalog problems today: skills live canonically in `.claude/skills` with `.agents/skills` symlinks (inverted against 15.1 and the Claude Code and Codex discovery rules in [14](research/14-codex-harness.md) and [15](research/15-claude-code-harness.md)); no skill has activation evals; `docs/agent-skills.md` is hand-maintained; `validate_skills.py` checks structure but not activation quality or staleness. Hard authority rules (no paid calls, no main promotion, no deploy) stay in AGENTS.md and become hooks or `permissions.deny`, not skill prose.

## 2. Target catalog for this repo (15 skills)

| Skill | Source | Job |
|---|---|---|
| `implement-task` | core | Take a ready roadmap item through the per-PR pipeline (worktree, tests, PR, review chain) |
| `review-change` | core | Independent review: correctness, security, tests, standards; reproduce findings |
| `verify-release` | core | Release profile checks, changelog, tags, post-deploy verification |
| `update-dependencies` | core | Handle the weekly Dependabot PR: read changelogs, fix breakages on the branch, keep CI green |
| `write-adr` | core | MADR 4 ADR from a decision, linked from docs |
| `resume-refactor` | core | Read RESUME, progress and tracker; continue the next milestone item |
| `score-repo` | core | Run `scorecard`, compare with ratchets, produce the three-lens evidence pack |
| `evaluate-assistant` | API | Run golden (cassette), retrieval metrics and the full set locally; read the report by stratum; add a golden item from a failure (schema-valid, canonical gold keys, native Spanish, no-retrieval ablation); never opens `evals/full/holdout.sealed.jsonl` |
| `change-prompt` | API | Edit a prompt file, update `prompts.lock`, run the `assistant-quality` profile locally, list needed re-records; re-recording only through `eval-record.yml` (spend is owner-only) |
| `refresh-contract` | API | Additive contract change with oasdiff, examples, consumer cross job and the expand/contract steps; breaking change needs ADR and `contract-major` |
| `api-change-use-case`, `api-change-stream`, `api-change-storage` | repo-specific (existing) | As in section 1 |
| `api-maintain-knowledge` | repo-specific (existing, trimmed) | Ingestion, provenance, graph |
| `api-refresh-corpus` | repo-specific (new, PAA-D2) | Refresh the frozen corpus snapshot from the approved public repository, update gold keys, report removed keys; only approved public content |

(7 core, 3 API catalog, 4 existing repo-specific and 1 new repo-specific skill: 15 in total, counting the three `api-change-*` skills separately.)

## 3. Skill rules and validation

| Item | Standard |
|---|---|
| Location | Canonical `.agents/skills/<name>/SKILL.md`; relative per-skill symlink `.claude/skills/<name>` to `../../.agents/skills/<name>` (PAA-D13); `check-skills` verifies every symlink |
| Form | `name` equals the directory (at most 64 characters); description starts "Use when ..." and states "Not for ..." (at most 1,024 characters, key trigger first); body at most 120 lines (hard cap 500); checklist, step-by-step procedure with exact commands, output template, feedback loop (verify, fix, re-verify), references one level deep, allowed tools listed; fragile steps as scripts under `scripts/`; `metadata: {owner, last-reviewed, version}`; no secrets or network calls |
| Activation evals | Each skill ships `evals/triggers.json` (at least 10 queries, about 20 recommended: 8 to 10 positive, 8 to 10 near-miss negatives, fixed 60/40 train/validation) and `evals/evals.json` (at least 3 output evals with assertions, with and without the skill). Protocol: 3 runs per query in a clean context; a positive passes at 0.5 or more, a negative at under 0.5; precision and recall reported on validation only. Gate: not merged if validation trigger accuracy drops by more than 10 points or the output delta turns negative |
| Near-miss examples | `evaluate-assistant`: negative "run the unit tests" (belongs to `implement-task`), "write a new retrieval rule" (belongs to `api-maintain-knowledge`) |
| Staleness | Monthly check of `last-reviewed`; 180 days opens an issue; lines that never change agent behaviour are deleted |
| Catalog doc | `docs/reference/agent-skills.md` generated from frontmatter; the validator compares |

## 4. Harness files committed in this repo (ecosystem 15.6)

| Path | Content for this repo |
|---|---|
| `AGENTS.md` | At most 200 lines: purpose, commands equal to CI (tested), branch flow, non-negotiables (no paid calls, no private career material, vps-ops boundary, sealed holdout), where plans live, skills list. The current owner-protection text is kept verbatim |
| `CLAUDE.md` | `@AGENTS.md` plus Claude-only lines (skills to run before done, subagents to use) |
| `.claude/settings.json` | Allow: lint, types, tests, build, read-only `gh` and `git`; ask: push, merge; deny: force push, `rm -rf`, reading `.env*`, reading `evals/full/holdout.sealed.jsonl`; hooks wired; marketplace from `engineering-standards` |
| `.claude/hooks/` | `format` (PostToolUse on edit and write), `guard-files` (block lockfiles, `.env*`, secrets), `guard-bash` (force push, `reset --hard`, `rm -rf` outside temp, `DROP DATABASE`, docker prune and `down -v`, `pkill -f`), `fast-check` on Stop with a loop guard |
| `.claude/agents/` | `test-runner` (haiku), `reviewer` (sonnet, high), `architecture-reviewer`, `eval-runner` (API repos: runs golden, retrieval and full-set commands, returns per-stratum numbers only, never opens the sealed holdout, no live runs), each read-only except implementers with `isolation: worktree` |
| `.codex/config.toml` | `approval_policy = "on-request"`, `sandbox_mode = "workspace-write"`, network off, hooks on, same guard rules; validated against the installed Codex version before commit |
| `.mcp.json` | None needed (no browser or Next.js tooling in this repo) |
| `.worktreeinclude` | Non-secret local files only (never `.env.local`) |
| `.github/workflows/agent-review.yml` | On PR: Codex review as second opinion (connector or `openai/codex-action` with `drop-sudo`); Claude review on request; minimal permissions, max turns and budget, no secrets for fork PRs |

Safety hooks and deny rules are repeated in this repo even when the shared plugin marketplace also provides them, because plugin subagents ignore hooks ([15](research/15-claude-code-harness.md)).

## 5. Review chain and delegation (ecosystem 15.2, 15A)

Each PR: author agent from a task branch `<type>/<milestone>-<slug>` in a worktree with test evidence; `ci-gate` green; independent reviewer agent (different context, read-only, given diff and rubric); second-model review (Codex via codex-second-opinion, advisory, every finding reproduced before acting; Claude reviewer on a different model tier if Codex is unavailable, recorded in the PR); architecture review for structural changes (the `src` rename, retrieval pipeline, contract v1.1, new dependencies); strongest agents for security, migrations and anything touching spend or privacy. Mechanical work suits a Codex worktree under `codex-delegate`: the 142 `no-untyped-def` annotations, ruff family rollouts, test relocation into lanes, docstring fixes, the `app` to `src` codemod; Claude reviews the diff, tests and secrets before commit. Test, build and CI log reading is delegated to the test-runner and log-analyst agents so the main thread keeps conclusions only. A missing, partial or failed review report is never treated as "no problems".

## 6. Hooks and permissions specific to this repo

| Rule | Mechanism |
|---|---|
| Never open `evals/full/holdout.sealed.jsonl` | `permissions.deny` read pattern, `eval-runner` agent prompt, CI check that a prompt or rule diff never mentions a holdout ID |
| No paid provider call from an agent session | No provider key in the environment; `ALLOW_PAID_AI=false` default; live workflows run only in the `eval-live` environment (branch restriction, code-level DR-04 hard stop, separate key; no reviewer click) |
| No push to `develop` or `main`, no `--admin` | `guard-bash`, rulesets without bypass |
| `pkill -f` banned | `guard-bash`; kill by verified PID |
