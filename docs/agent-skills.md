# Repository agent skills

`AGENTS.md` remains the canonical operating contract. `CLAUDE.md` explicitly imports
it with `@AGENTS.md`; no client is assumed to read the other's entry point.
Skill instructions live only in `.claude/skills/<name>/SKILL.md`. Codex discovers
relative directory symlinks under `.agents/skills/`. There are no independently
editable instruction copies, hooks, tool-permission grants or global installations.

## Catalog

| Skill | Recurring task |
| --- | --- |
| `api-change-use-case` | Application policy, conversations, ownership and atomic limits |
| `api-change-stream` | Provider/LangGraph lifecycle, incremental SSE and frontend contract |
| `api-maintain-knowledge` | Approved public ingest, provenance, GraphRAG and retrieval evaluation |
| `api-change-storage` | Migrations, transactions, accounting, deletion and recovery |
| `api-verify-release` | Scoped verification/security review, CI, containers and release preparation |

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
`description` strings, matching the folder name. Use an `api-` action-oriented name
and a description distinguishing neighboring tasks. Do not add client-specific
interpolation, permission fields or copied universal programming advice. Link
resources with paths relative to SKILL.md, staying inside the checkout; run listed
commands from the repository root. Add scripts only for repeated deterministic work.

For a new skill, create its relative Codex link from the repository root:

```sh
ln -s ../../.claude/skills/api-new-task .agents/skills/api-new-task
uv run python -m scripts.validate_skills
uv run pytest -q tests/test_skills.py
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
and limitations in `docs/verification/agent-skills.json`.

## Inventory and compatibility

Initial inventory: only AGENTS existed. Retain/improve that canonical contract;
add the Claude entry and five focused workflows. There were no existing skills,
callers or resources to consolidate/retire. No old skill was deleted.

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
   `$api-verify-release Review only; identify the checks for a pure policy change`.
3. In Claude Code, inspect the `/` skill menu and `/memory` (AGENTS import), then
   invoke `/api-verify-release` with the same read-only request.
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
