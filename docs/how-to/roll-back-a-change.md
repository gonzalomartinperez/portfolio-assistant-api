# Roll back a change on `develop`

Use this when a merged pull request breaks `develop` and a fix-forward is not ready within one hour of
agent work (ecosystem 15A, failure handling). A rollback is an ordinary pull request: it goes through
`ci-gate` like any other change. Never force-push `develop` or `main`, never use `--admin`.

## Steps

1. Find the merge commit of the pull request to undo:

   ```sh
   git fetch -q
   M=$(gh pr view <pr> --json mergeCommit --jq .mergeCommit.oid)
   ```

2. Revert it on a task branch from fresh `origin/develop`. `-m 1` keeps the `develop` side of the merge:

   ```sh
   git worktree add -b revert/<slug> ../wt/<repo>-revert origin/develop
   cd ../wt/<repo>-revert
   git revert --no-edit -m 1 "$M"
   git commit --amend    # Conventional title "revert: ...", reason, attribution
   ```

3. Check that the revert touches exactly the files of the original pull request:
   `git show --stat HEAD` against `gh pr view <pr> --json files`.
4. Push, open a pull request into `develop` with the reason and the original PR link, wait for a green
   `ci-gate` and merge with a merge commit (`gh pr checks <n> --watch && gh pr merge <n> --merge --delete-branch`).
5. To re-apply once the cause is fixed, revert the revert's merge commit the same way, then add the fix
   on top in the same pull request or in the next one. Re-applying without the fix brings the breakage back.
6. If the change was a migration, a revert of the code does not undo the schema. Follow the
   [query-index migration and rollback](../reference/deployment-contract.md#query-index-migration-and-rollback)
   section instead, and never drop data to roll back.
7. If the change was already promoted to `main` or deployed, stop: `main` changes only by release (OD-11),
   and production rollback belongs to vps-ops (pin the previous image digest in `releases/production.lock`).

## Rehearsal record (M6, 2026-11-22)

| Step | Pull request | Result |
|---|---|---|
| Original change (ADR 018, docs only, chosen so the rehearsal changes no runtime behavior) | [#222](https://github.com/gonzalomartinperez/portfolio-assistant-api/pull/222), merge `0ae1261` | merged on a green `ci-gate` |
| Revert with `git revert -m 1 0ae1261` | [#224](https://github.com/gonzalomartinperez/portfolio-assistant-api/pull/224), merge `62262a2` | merged on a green `ci-gate`; four files restored exactly |
| Re-apply with `git revert -m 1 62262a2`, plus this page | this pull request | see its checks |

Time from the revert branch to the revert merge was within one CI cycle, well under the one-hour budget.
