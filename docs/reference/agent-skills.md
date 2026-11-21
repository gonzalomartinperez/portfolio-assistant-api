# Repository agent skills

`AGENTS.md` remains the canonical operating contract. `CLAUDE.md` explicitly imports
it with `@AGENTS.md`; no client is assumed to read the other's entry point.
Skill instructions live only in `.agents/skills/<name>/SKILL.md`. Claude Code discovers
relative directory symlinks under `.claude/skills/`. There are no independently
editable instruction copies, tool-permission grants or global installations. Safety
hooks and permission rules are in `.claude/hooks/` and `.claude/settings.json`, not in skills.

## Catalog

Fifteen skills: seven core, three API and five repository-specific
([master plan](../master-plan/skills.md) section 2).

| Skill | Group | Recurring task |
| --- | --- | --- |
| `implement-task` | core | One roadmap item through worktree, tests first, selected checks, PR into `develop` and review chain |
| `review-change` | core | Independent read-only review of a diff with reproduced findings; security review delegates to `owasp-security-review` |
| `verify-release` | core | Release profile, images and manifest, tags, changelog and post-deploy evidence |
| `update-dependencies` | core | The weekly Dependabot PR: fix breakages on its branch, owner merges |
| `write-adr` | core | MADR 4 decision record in `docs/decisions/` |
| `resume-refactor` | core | Resume the master refactor from git and `docs/master-plan/` |
| `score-repo` | core | Scorecard evidence against ratchet baselines (offline) |
| `evaluate-assistant` | API | Offline retrieval and fixture evaluations, reports by stratum, schema-valid eval items; never the sealed holdout |
| `change-prompt` | API | Edit a prompt under `src/portfolio_assistant/prompts`, regenerate `prompts.lock`, list needed re-records (owner-only) |
| `refresh-contract` | API | Additive contract change with `contracts.export`, examples and consumer steps; breaking changes need an ADR |
| `api-change-use-case` | repo | Application policy, conversations, ownership and atomic limits |
| `api-change-stream` | repo | Provider/LangGraph lifecycle, cancellation and incremental SSE |
| `api-change-storage` | repo | Migrations, transactions, accounting, deletion and recovery |
| `api-maintain-knowledge` | repo | Approved public ingest, provenance, GraphRAG and retrieval logic |
| `api-refresh-corpus` | repo | Refresh the frozen public corpus snapshot and report removed gold keys |

The core skills come from engineering-standards v1.0.0 (`harness/skills/`), tuned to this
repository. Evaluation content left `api-maintain-knowledge` for `evaluate-assistant`.

`api-verify-release` was retired in master plan task M3-6. Where its content went:

| Content | Now in |
| --- | --- |
| Release profile, CI run inspection, image scan policy, immutable manifest, tags, post-deploy ownership | `verify-release` |
| Binding rules: no Infisical, Redis, secret SDK or deployment controller; no old merge flags or native auto-merge; PGDATA UID 70 volume rule; `--authorize-export` authority; local-and-CI-only Compose; ensurepip check | `verify-release`, section "Task-specific references" |
| Pointers to runtime baseline, private observability, synthetic export, live-evaluation readiness, ADR008, analytics direct edge | `verify-release`, same section |
| Choosing and reading checks by risk (policy, HTTP/SSE, persistence, CI and container, provider transport, contract, evals) | `implement-task` |
| Focused security review, secret scan, threat model | `review-change` (delegates to `owasp-security-review` and `gha-security-review`, with a manual fallback) |
| Weekly dependency PR, owner merges | `update-dependencies` (already existed; unchanged), plus the binding rule above |

Not carried over, because they are one-off dated procedures that live in their own records: README gallery capture
and diagram rules ([readme-gallery](../evidence/archive/2026-10/readme-gallery.md), [diagrams](../explanation/architecture.md)), database access-path
measurement ([database-queries](../evidence/archive/2026-10/database-queries-2026-10-17.md)) and the provider transport evidence
([provider-transport](../evidence/archive/2026-10/provider-transport-2026-10-17.md)). Load those documents directly for such tasks.

Every skill carries `metadata` (owner, last-reviewed, version) and an `evals/` folder (`triggers.json`,
`evals.json`); none has `allowed-tools` because this catalog rejects permission fields, so each states its tools in prose.

Routine onboarding reads README and AGENTS; it does not load this whole catalog.
Coding standards remain in CONTRIBUTING. Conditional operational detail lives in
existing maintained documentation, not duplicated skill references. Each skill
states its inputs, relevant boundaries, evidence and stopping conditions.

## Invocation and authority

From a trusted checkout, Codex: `$api-change-stream investigate cancellation`.
Claude Code: `/api-change-stream investigate cancellation`. Descriptions also
permit natural-language discovery. No explicit-only settings are enabled.

Skills are guidance, not permission: an investigation or review stays read-only.
A request to prepare a deployment never authorizes running it. Commits, PRs, merges,
paid calls, secrets and production each remain subject to the current task's
scope/authority. A previous assignment's merge permission is not a permanent rule.
The frontend and portfolio belong to other owners; career-ops is not a public source.

## Maintenance and validation

Edit only the canonical folder. Keep YAML frontmatter to portable `name` and
`description` strings, matching the folder name, plus the optional `metadata` mapping
(exactly `owner`, `last-reviewed`, `version`, as strings) used by the shared skills.
Use an `api-` action-oriented name (the seven core and three API catalog skill names are the only exception)
and a description distinguishing neighboring tasks. Do not add client-specific
interpolation, permission fields or copied universal programming advice. Link
resources with paths relative to SKILL.md, staying inside the checkout; run listed
commands from the repository root. Add scripts only for repeated deterministic work.

For a new skill, create its relative Claude Code link from the repository root:

```sh
ln -s ../../.agents/skills/api-new-task .claude/skills/api-new-task
uv run python -m scripts.validate_skills
uv run pytest -q tests/harness/test_skills.py
```

Replace the example name with the actual canonical directory. The validator uses
the existing PyYAML 6.0.3 package, now an explicit development dependency, and the
repository's redacted secret-pattern detector. It checks metadata, discovery links,
name collisions, local references/command modules, executable shell resources,
scaffolding, private paths and known secret patterns. It never executes skill
instructions or follows external URLs. The static CI job runs it before Python
checks; negative tests verify that broken catalogs fail. Run the full existing
verification suite for code changes. Known-pattern scanning is not proof of secrecy.

After editing descriptions, review the should/should-not-route cases in
`tests/fixtures/skill_scenarios.json`. These are behavioral evaluation inputs, not
a keyword classifier pretending to prove model selection. Record actual outcomes
and limitations in `docs/evidence/archive/2026-10/agent-skills.json`.

## Activation evals

Each skill ships `evals/triggers.json` (about 20 queries: positives, near-miss negatives that name the
sibling skill that should win, and a fixed 60/40 train/validation split, `runs_per_query` 3) and
`evals/evals.json` (at least three output evals with assertions). Measure activation locally, never in CI:

```sh
uv run python -m scripts.skill_activation_eval --dry-run --skills write-adr
uv run python -m scripts.skill_activation_eval --out artifacts/activation.json --jobs 4
uv run python -m scripts.skill_activation_eval --skills <name> --out artifacts/activation.json
```

The tool lists every skill's `name: description` and one query in a clean `claude -p --model haiku` call
(subscription only: every `ANTHROPIC_*` variable is removed from the child environment; no tools, empty directory) and records which skill the router would load. Failed router calls are excluded from the fraction, recorded as `errors` in the JSON, and make the run exit 1. A positive
passes at a trigger fraction of 0.5 or more, a negative below 0.5; precision, recall and accuracy are reported on
the validation split (train for information). Re-running a skill (same `--split`) into an existing `--out` file keeps its
`first` numbers and replaces `final`. The gate is that a skill's final validation accuracy does not fall more than
10 points below its first. Results are routing evidence for a small model, not proof of behavior; the latest are in
[docs/evidence](../evidence/skills-activation-2026-11-14.md).

## Inventory and compatibility

Initial inventory: only AGENTS existed. Retain/improve that canonical contract;
add the Claude entry and five focused workflows. There were no existing skills,
callers or resources to consolidate/retire. No old skill was deleted at that time;
`api-verify-release` was retired in master plan task M3-6 after its content landed elsewhere.

Test environment: Linux/WSL, Git symlinks, Codex CLI **0.157.1**, Claude Code
**2.1.283**. These are locally observed versions, not a promise about every release.
Windows checkouts must preserve directory symlinks (`core.symlinks=true` where
supported), or use WSL. A flattened link file is rejected by validation; there is
no silent duplicate-copy fallback.

Client discovery and explicit expansion can be tested without model intelligence.
Offline transport probes do not prove natural-language routing, judgment or policy
adherence by a real model. No paid calls are authorized for this validation.
For a separately authorized live check in a disposable clone:

1. Run the catalog validator and record `codex --version` / `claude --version`.
2. In Codex, open `/skills` and check each `api-` name occurs once; invoke
   `$implement-task Review only; identify the checks for a pure policy change`.
3. In Claude Code, inspect the `/` skill menu and `/memory` (AGENTS import), then
   invoke `/implement-task` with the same read-only request.
4. Run the positive, negative, missing-prerequisite and scope-expansion scenarios.
   Record selection, commands, output and tracked/untracked changes before/after;
   a read-only scenario must produce no edits, commits, GitHub or deployment actions.
5. Exercise the fixture workflow from local-development only when permitted, with
   a unique Compose project/unused loopback ports. Never select shared/production
   services to fill a missing prerequisite. Report omissions instead of fabricating
   compatibility or live-model success.

## Official references consulted · 2026-09-27

- [Codex skills](https://developers.openai.com/codex/skills) (currently redirects to
  [Build skills](https://learn.chatgpt.com/docs/build-skills)): metadata discovery,
  explicit/implicit use and symlinked skill folders.
- [Claude Code skills](https://code.claude.com/docs/en/skills): project skill discovery,
  slash invocation and portable name/description versus client-specific fields.
- [Claude project memory](https://code.claude.com/docs/en/memory): explicit local imports.

Keep discovery separate from authorization. No skill disables permission prompts,
selects a production target or treats roadmap entries as approval.

On 2026-10-03, catalog validation and workflow tests were rerun after the knowledge
sync updates. Available clients report Codex CLI 0.160.0 and Claude Code 2.1.288.
Those version checks do not establish fresh model invocation or implicit-routing
compatibility; the earlier client discovery evidence above remains separately dated.

## Refreshed discovery and automatic selection · 2026-10-18

Codex CLI 0.163.0 actually discovered all five repository skills through app-server
skills/list with forceReload, including the relative discovery links. Claude Code
2.1.292 actually returned all five commands in its stream-JSON initialize response
with project settings enabled. Both probes submitted zero model turns; Claude's
model endpoint was an unreachable loopback address and extra MCP configuration
was empty. Only safe names/counts are retained in [the discovery receipt](../evidence/archive/2026-10/skill-discovery-2026-10-18.json),
not raw initialization payloads.

All skills remain eligible for automatic selection by task. Explicit commands above
are optional ways to choose one, never prerequisites. Frontmatter is the portable
name/description core; disabling Claude model invocation is rejected. Optional
Codex policy metadata may omit allow_implicit_invocation or set it to true, never
false. Structural negative tests enforce that invariant. Description triggers remain
focused on real use cases; there is no catch-all or permission expansion.

This proves discovery, not model-driven task selection or execution. The documented
positive/nearby-negative/read-only/scope-escalation scenarios remain the behavioral
review procedure; no paid model campaign was launched for client verification.
Official documentation rechecked:
[Codex skills](https://developers.openai.com/codex/skills),
[app-server skills/list](https://developers.openai.com/codex/app-server) and
[Claude skill discovery](https://code.claude.com/docs/en/skills).
