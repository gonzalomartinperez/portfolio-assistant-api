## What

<!-- What changes, in two to four sentences. The PR title is a Conventional Commit. -->

Closes #<!-- issue or roadmap item, e.g. M1-07 -->

## Why

<!-- The problem, decision or roadmap item this serves. -->

## Evidence

<!-- CI run URL, local commands and their result. State fixture and live verification separately. -->

- [ ] Local checks pass (`just check` and `just test`)
- [ ] `ci-gate` green

## Risk

<!-- API/SSE compatibility, migrations, privacy implications, who is affected, what could break. -->

## Rollback

<!-- How to roll back: revert the merge commit, redeploy the previous image digest, migration down path. -->

## Checklist

- [ ] Tests at the right layer (domain, application, adapter, HTTP/SSE contract)
- [ ] Docs or ADR updated where behavior changed (or not needed)
- [ ] Contracts regenerated with `uv run python -m contracts.export` if HTTP changed (or not applicable)
- [ ] No secrets, no real API key, no private career-ops material, fixture mode still the default
- [ ] AGENTS.md, skills or hooks updated where agent behavior changed (or not needed)

## Review chain

- [ ] Independent reviewer agent findings answered
- [ ] Second-model review (Codex) findings reproduced and answered, or fallback recorded
- [ ] Architecture review for structural changes (or not structural)
