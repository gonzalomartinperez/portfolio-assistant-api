# Development workflow

## Spec-driven, proportionate to the change

Use a short specification for each substantive feature under
`docs/specs/<short-kebab-case-name>.md`. Start from [the template](specs/template.md).
Keep the intended behavior and acceptance criteria stable while updating the plan
as implementation teaches us more. Record meaningful deviations and their reasons.
An issue or explicit task is sufficient for a small fix; do not create paperwork
that duplicates an existing source of truth.

Statuses are `draft`, `ready`, `in-progress`, and `done`. A spec becomes `ready`
when scope and consequential choices are resolved, not merely because an agent
wrote it. Mark it `done` only after acceptance criteria have verification evidence.
Keep unfinished checks explicit. Specifications describe requirements; they do not
grant permission to publish, spend money, access accounts, or change infrastructure.

## Design and implementation

Use [Readable code and useful documentation](code-quality.md) for design,
comments, JSDoc and the final clarity review. It is shared by both agent hosts.
For public text and visual evidence, read [editorial guidelines](editorial-guidelines.md)
and the relevant section of the [public-content contract](public-content.md).

- Keep routes in `src/app/`. Colocate feature code first; extract shared components
  or utilities when actual reuse or a meaningful boundary justifies it.
- Prefer focused functions, explicit inputs, descriptive names, composition, and
  small modules. Avoid generic repositories, service layers, or dependency injection
  frameworks for a static portfolio.
- Default to Server Components. Add a narrow client boundary only for browser state
  or interaction. Keep secrets and privileged logic server-side.
- Use semantic HTML, visible keyboard focus, accessible names, readable contrast,
  responsive layouts, and reduced-motion support when adding animation.
- Validate untrusted input at system boundaries. Do not use unsafe HTML rendering
  for content that can be represented as ordinary React elements.
- Use Next.js image and metadata capabilities when relevant. Measure performance
  before adding caching or memoization; record the measurement conditions.
- Keep TypeScript strict. Prefer narrowing and real types to `any`, assertions,
  ignored errors, or duplicated state. Comments explain constraints and reasons.

## Verification

Run `npm ci` after dependency changes, then `npm run check` and `git diff --check`.
`check` covers repository invariants, lint, formatting of Biome-supported files,
and one build with mandatory TypeScript validation;
it does not provide a security audit or visual accessibility QA. After building,
`npm run test:smoke` checks the production server, HTML landmarks, and 404 handling;
The Hostinger compatibility job runs it too. It uses port 3100 by default; set
`SMOKE_TEST_PORT` for parallel runs. The modern quality job uses `npm run test:site`:
one owned production server serves rendered assertions and Playwright sequentially.
Rendered tests already cover the smoke assertions, so they are not repeated there.
Browser tests default to one worker to avoid competing software-rendered scenes;
see the [motion research](research/motion-performance.md) for measurements and rationale.
Native image-tab tests use the full Chromium channel instead of headless shell
to exercise browser document navigation. Install Chromium without `--only-shell`;
the CI installation already provides both binaries. Other tests retain their runtime.
Use `SITE_TEST_PORT` to isolate this combined run; standalone browser tests retain
their own managed server. Document hashes and signature checks run before the build.
Use `npm run typecheck` for a quick standalone type check during development;
there is no need to run it immediately before `check`. Reuse successful verification
for an unchanged source state, dependencies and runtime; rerun affected checks
after changes rather than repeating the full suite at each agent handoff.
`test:repository` checks tracked/unignored source text, simple inline Markdown file links,
skill adapter metadata/targets, and exact Next.js/SWC lockfile alignment. It does
not validate external URLs, Markdown anchors, or the behavior of an agent host.

Resolve warning causes through supported settings. Do not filter stderr, patch
dependencies, set internal test flags, or disable validation to obtain a quiet log.
Document expected platform fallback messages and their exit criteria in the
[deployment guide](deployment.md#build-messages).
For user-facing changes, check production behavior, keyboard access, mobile and
desktop layouts, and relevant error/empty/loading states. Add regression tests for
bugs and focused behavioral tests as functionality appears. Select a maintained,
compatible test tool for the actual layer; do not install a suite just to count tests.

Review the exact staged diff for private information, unexpected artifacts, and
scope creep. Dependency auditing is an additional signal, not proof of security.
Never put private career documents, account details, or personal work histories in
specs, examples, commits, or prompts stored in this public repository.

### Task-specific QA

Select checks for the changed behavior; the release still runs the required CI.
Do not repeat successful checks on unchanged inputs just to inflate a handoff.

| Change | Verification focus |
| --- | --- |
| Shared layout, navigation or copy | All eight routes in both languages (16 paths), both themes, narrow mobile and desktop, keyboard, 200% zoom and horizontal overflow. Check localized wrapping rather than assuming English proves Spanish. |
| Education or CV layout | Grade chips remain inside their rows with readable labels; CV heading, sections and downloads share the intended content width. Review long course names and both locales. |
| Hero or interaction | Forward/reverse deterministic scroll states, rapid reversals, all rows of the expanded toolkit reachable by native scroll, no overlap with following content; avatar pulses return to rest without obscuring essential controls. |
| Motion changes | Reduced motion, no WebGL, context loss, hidden tab, navigation cleanup and touch versus scroll gestures. Use actual measured conditions; emulation is not evidence of physical-device FPS. |
| Assets, documents or CV | Local files, provenance, proportions, accessible context, document hashes and actual served downloads; source and generated outputs agree. |

Existing browser coverage lives in [tests/browser](../tests/browser/), including
route, education, document, scene-toolkit, scene-stability and sphere-pulse tests.
Extend the relevant suite when fixing a regression; screenshots supplement
behavioral assertions rather than replacing them. Record untested devices or
states explicitly. A documentation-only handoff may report repository/link and
skill checks without claiming that application or hosting QA was repeated.

The modern quality job owns lint, content checks, one type-checked build, budgets
and rendered/browser checks. The separate Hostinger job owns the GLIBC 2.28
baseline, observed runtime, SWC WASM fallback, build and smoke check. Do not add
Biome to the hosting build or duplicate the full browser suite there. Preserve
the `Quality checks` aggregator and protected branch checks; deployment evidence
remains separate from CI, as described in [deployment](deployment.md).

## Agent entrypoints and skills

Codex loads root `AGENTS.md` and discovers `.agents/skills/`. Claude Code loads
`CLAUDE.md`, which imports the same contract, and discovers `.claude/skills/`.
The Claude skill files are thin adapters; edit procedures only in `.agents/skills/`.
Keep each adapter's name and description aligned with its canonical skill.
This avoids symlink requirements on Windows and keeps procedures in one place.

| Skill | Use |
| --- | --- |
| `specify-feature` | Scope, acceptance criteria, design decisions, and a delivery plan |
| `implement-feature` | A tested vertical slice with clean, accessible Next.js code |
| `debug-issue` | Reproduction, root cause, and an authorized regression fix |
| `review-change` | Read-only correctness, security, accessibility, and maintainability review |
| `update-dependencies` | Compatible stable upgrades with lockfile and regression checks |
| `prepare-delivery` | Final verification and an authorized commit or push |

Invoke a skill as `$specify-feature` in Codex or `/specify-feature` in Claude Code.
Restart or refresh discovery in the host after adding skills. Verify discovery there;
file validation alone cannot demonstrate that an installed host loaded a skill.
These are instruction workflows, not sandbox controls. No permissions are relaxed,
no MCP servers are installed, and no publish hooks run automatically.

## Parallel agents and worktrees

Prefer parallel execution when at least two substantial tasks can proceed
independently. Do not split trivial fixes or tightly coupled changes just to use
more agents. Stay within host limits and use one coordinator with a small number
of bounded lanes; if delegation is unavailable, follow the same plan serially.

1. Inspect Git status, current remotes, and registered worktrees. Fetch develop
   before assigning work. Define shared interfaces and dependencies first.
2. Assign each writing agent a dedicated registered worktree and a standard task
   branch based on develop. Keep worktrees outside the canonical checkout and
   validate their resolved paths and common Git directory. Do not make independent
   clones, reuse active paths, or check out one branch in multiple worktrees.
3. Give each lane an objective, base commit, allowed files, acceptance criteria,
   commands, and known dependencies. State that other agents are working and their
   changes must be preserved. One owner per file; the coordinator owns shared
   interfaces, manifests, lockfiles, workflow files, and cross-cutting configuration.
4. Install dependencies per worktree using its pinned Node version. Do not share
   node_modules, generated types, or build output between worktrees. Assign distinct
   local ports to concurrent servers and stop only processes started by that lane.
5. Serialize integration through task PRs into develop in dependency order. Rebase or merge the
   latest develop into an unpublished task branch as appropriate; prefer merging
   once a branch is shared to avoid force-pushes. Rerun affected checks after
   integration changes. Only develop may open the release PR into main.
6. Handoffs record objective, worktree, branch, base and result commits, changed
   files, dependencies, checks and results, spec coverage, and remaining risks. Detached registered worktrees may
   be used for read-only reviews without creating a writing branch.
7. After integration, verify the remote PR is merged and the local worktree is
   clean, including untracked files, and its agent is no longer active. Remove the worktree through Git, not recursive filesystem deletion;
   prune stale remote refs and delete the integrated local task branch without
   force. Preserve unmerged commits, dependencies needed by active work, and QA
   artifacts until reviewed. Keep main, develop, and the canonical checkout.

Do not nest delegation without an independent task and available capacity. A lane
blocked on another lane should report its dependency rather than edit the other's
files. The coordinator alone handles protected-branch PR promotion and confirms
the complete integrated release, not just individual lane results.

## Commit convention

Browser retries retain diagnostic evidence in CI, but a test that passes only on
retry still fails the quality gate. Fix synchronization or reproduce the actual
regression instead of treating intermittent results as release approval. Avoid
running independent browser suites concurrently on the same local machine when
measuring scene stability; preserve traces and rerun a timeout in isolation.

### Protected integration flow

`task branch -> PR -> develop -> PR -> main`

Start task branches from updated `develop`; use `feat/`, `fix/`, `chore/`, `docs/`,
`refactor/`, `perf/`, `test/`, `ci/`, `build/`, or `revert/` followed by a lowercase
kebab-case description, for example `feat/project-gallery`. The policy checks this
pattern for task PRs. Only same-repository Dependabot-authored PRs may use the bot's
native `dependabot/npm_and_yarn/` or `dependabot/github_actions/` naming format.
`develop` is the integration branch, while `main` is the production
branch connected to Hostinger. Only same-repository `develop` is a valid PR source
for `main`. Dependabot targets `develop` as well.

Both branches require PRs, up-to-date quality checks, the `Branch policy` check,
and resolved review conversations. Direct pushes, force-pushes, and branch deletion
are blocked, including for administrators. Do not push locally created merge commits
to either branch. Use GitHub PR merge commits; squash and rebase merging are disabled
to preserve the ancestry of repeated develop-to-main releases. Retain both branches.
Merge the latest target into the task branch to resolve conflicts; never reset a
shared branch. If develop needs main's latest merge commit, integrate it through a
sync task branch and PR into develop.

GitHub automatically deletes task branches after merging. Protected `main` and
`develop` are retained. Locally, fetch with pruning, verify the task branch is
integrated and its worktree is clean, then use non-forced branch deletion. Never
delete another contributor's unmerged work or remove an active worktree.

The branch-policy workflow runs from the trusted base via `pull_request_target`,
reads PR metadata only, and has no checkout, dependency installation, or secrets.
Do not add PR code execution to it. An invalid PR can still be opened, but its check
fails and blocks merging. CI separately tests PR code with read-only permissions.

No second-person approval is required for this solo repository, but the PR and
required checks remain mandatory. Hosting configuration and branch protection are
account-side controls, not established merely by these files. A repository owner
can change those settings; agents must never relax them to finish a task.

Use `type(scope): imperative summary`, with a meaningful scope when useful.
Keep the subject concise, then explain why the change is needed and any tradeoffs.
Record validation and limitations in the body. Use `BREAKING CHANGE:` and issue
references only when they actually apply. Do not invent issue IDs or claim tests ran.
Prefer one coherent change per commit, with no credentials or local absolute paths.
Pushing is a separate external action and requires user authorization.

## Sources

Checked on 2026-09-12. SDD here is a repository convention, not a claim that either
agent vendor mandates a universal development process.

- [Codex instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code memory and imports](https://code.claude.com/docs/en/memory)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
