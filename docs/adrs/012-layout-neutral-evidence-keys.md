# ADR012: Compare evidence by layout-neutral canonical keys

Status: accepted (2026-11-14, master plan task M1-1, decision PAA-D3).

## Context and problem

The public portfolio moved its profile files from `src/content/<locale>/<topic>.ts`
to `content/<locale>/<topic>.ts`. The API indexes both layouts
([content layout coordination](../coordination/portfolio-content-layout.md)) and keeps
the physical path in citations, because citation URLs must point at the real file
at the indexed commit.

The retrieval cases in `evals/retrieval.json` named the expected evidence by
physical path. Against the current portfolio, hybrid retrieval returned the right
files under the new root and the cases still failed: 2 of 9 passed instead of the
8 of 9 measured on the old root (master plan audit, P0-1). The failure came from
the expected data, not from retrieval.

## Decision

1. One domain function, `canonical_key(path, entity=None)` in
   `app/domain/portfolio_paths.py`, maps every approved profile path to
   `<locale>/<topic>`, optionally followed by `#<entity>` (a lowercase kebab-case
   slug, for example `en/projects#filomena`). Both layouts give the same key.
   Approved non-profile paths are already layout-stable and come back unchanged.
   `key_paths(key)` is the inverse and returns both physical paths, current
   layout first.
2. Retrieval cases are qrels: `qrels` maps canonical keys to a relevance grade
   (`1` today). Cases with no expected evidence (`no-answer`, `ambiguity`) have
   empty qrels. Physical paths no longer appear in expected data.
3. Graders, harnesses and tests compare canonical keys and never raw paths.
   Citations keep the physical path and URL.

## Consequences

- The same case file grades both layouts. A future content-root move changes the
  path helpers (`PROFILE_PATH_PATTERN`, `profile_paths`) and the adapters that
  query both roots, but no expected evaluation data.
- The later eval harness (golden items, ranx qrels, graders, master plan M2) uses
  the same keys.
- Entity-level keys can be added to qrels without changing the file format.

## Confirmation

- `tests/test_portfolio_paths.py`: both layouts share one key for every
  locale/topic pair, a Hypothesis round-trip property
  (`key_paths(canonical_key(path, entity))`), non-profile paths stay unchanged,
  and invalid keys and slugs are rejected. The same file checks that
  `evals/retrieval.json` uses only valid canonical keys.
- `tests/test_retrieval_layouts_integration.py` (integration lane): indexes the
  pinned public corpus under both content roots with fixture embeddings, runs
  every retrieval case with hybrid retrieval, requires identical per-case
  outcomes on both layouts (pass/fail and the retrieved qrels keys; tie-ranked
  secondary evidence may differ because chunk ids include the physical path), and requires every case to pass (answerable cases
  retrieve their qrels; no-answer and ambiguity cases retrieve nothing).
