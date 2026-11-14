# ADR016: Frozen in-repo snapshot of the approved public corpus

Status: accepted (2026-11-14, master plan task M2-2, decision PAA-D2).

## Context and problem

The `database` and `container` CI jobs checked out `gonzalomartinperez/portfolio` at the
pinned commit `1acbe54906c88398652aebb8eae0c217fd0d8821` to index the approved public
corpus, and checked out `portfolio-backoffice` for IAM compatibility and the optional
private contract-bytes comparison. Every pull request therefore depended on other
repositories being reachable and readable, and the corpus identity lived in workflow YAML
rather than in reviewable data.

## Options

1. **Pinned checkout (status quo).** Small repository, but a cross-repo token and network
   dependency on every PR, and the evaluated corpus is not visible in this repository.
2. **Frozen snapshot in `evals/corpus` (chosen).** About 12 small text files, all public,
   committed with a hashed manifest. No network, reviewable diffs, deterministic identity.
3. **Git submodule.** Still a cross-repo fetch in CI and a moving pointer.

## Decision

1. `evals/corpus/` holds exactly the files the indexer reads (`ROOT_PATTERNS` in
   `app/adapters/portfolio/indexing.py`) at the pinned portfolio commit, in the same
   relative layout (the legacy `src/content/<locale>/` root at that commit).
2. `evals/corpus/manifest.json` records the repository, commit, commit date, per-file
   sha256 and byte size, the layout-neutral canonical key
   ([ADR012](012-layout-neutral-evidence-keys.md)), and
   `corpus_snapshot_id = corpus-<first 12 hex of sha256 over the sorted (path, sha256) pairs>`.
   Current value: `corpus-a4e4aa84b466`.
3. `uv run python -m app.knowledge_sync --source snapshot --repo evals/corpus` indexes the
   directory. Blob ids are Git object ids of the bytes and the commit is the manifest's
   portfolio commit, so chunk identities, versions and citation URLs equal those of the
   Git mode, which keeps working.
4. `scripts/refresh_corpus.py --source <checkout> --ref <commit>` rebuilds the files and
   manifest and prints keys added and removed; `--check` verifies offline.
5. The `database` and `container` jobs check out no other repository. The backoffice IAM
   compatibility run and the `frontend_commit` contract-bytes comparison move to
   `.github/workflows/cross-repo.yml` (nightly and `workflow_dispatch`), outside `ci-gate`.

## Consequences

- The corpus changes only by an explicit PR that runs the refresh script and shows the
  manifest diff; no other change may touch `evals/corpus`.
- Backoffice incompatibilities surface nightly instead of on the offending PR.
- OD-76 (refreshing the snapshot to a current portfolio copy) is pending; until then the
  snapshot stays at the commit above and its `src/content` layout.
- The snapshot contains only approved public content; the secret pattern check in the
  indexer still runs on every file.

## Confirmation

- `tests/tooling/test_corpus_snapshot.py`: manifest hashes match the files, the snapshot
  id is stable and recomputable, `refresh_corpus --check` passes and detects tampering,
  canonical keys cover `en` and `es`, snapshot indexing sources match Git blob ids.
- `tests/tooling/test_ci_no_cross_repo.py`: `ci.yml` has no `repository:
  gonzalomartinperez/` checkout, and `cross-repo.yml` is pinned, token-less and
  least-privilege.
- `tests/test_release.py`: the contract-bytes guard lives in `cross-repo.yml`.
