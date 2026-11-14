# Full evaluation tier (assistant-quality.md section 6)

Report-only: this tier has no pass gate. It exists to find new failures; real failures are
promoted to golden. Regenerate nothing by hand: `evals/harness/distill_full.py` (deterministic,
no network, no model) wrote these files from `evals/archive/legacy-2026-10/` and the authored
spec `evals/harness/full_spec.json`.

| File | Content |
|---|---|
| `full.jsonl` | 384 development items (this README, tests and agents may read it) |
| `holdout.sealed.jsonl` | 100 sealed items. Never open, print, grep or quote it (AGENTS.md); read only through `evals.harness.loader.sealed_aggregate` |
| `manifest.json` | sha256 per development item, counts, the holdout file sha256 and counts only, `corpus_snapshot_id` |
| `selection.json` | dropped families with scores and reasons, the duplicate rule, the size note |

## Composition (about 484 = 384 development + 100 sealed)

| Part | Development (EN / ES) | Sealed (EN / ES) | Source |
|---|---|---|---|
| Intent families | 304 (152 / 152) | 80 (40 / 40) | 96 of 100 legacy families x 2 locales x {direct, conversational}; 76 families development, 20 old-holdout families sealed and rephrased natively |
| Adversarial | 40 (20 / 20) | 10 (5 / 5) | all 40 legacy prompts (20 EN/ES pairs, balanced); 10 new sealed |
| Multi-turn | 20 (10 / 10) | 0 | 15 legacy scenarios (one locale each; 8 rewritten natively in the other locale or adapted) + 5 new (2 language switch, topic drift, 2 history poisoning) |
| Cross-lingual and edge | 20 (10 / 10) | 10 (5 / 5) | new: terms of the other language, no accents, mixed language, regional vocabulary, unsupported input languages |
| **Total** | **384 (192 / 192)** | **100 (50 / 50)** | EN minus ES is 0 overall and per part |

**Size: about 484, above the plan's 450.** Section 6.1 lists 450 items and 6.2 builds the holdout
from the same 450; here the sealed 80 + 10 + 10 replace development items instead of adding to
them, but only four legacy families qualify as real duplicates (plan: 10) and all 40 legacy
adversarial prompts are kept (plan: "the existing 40"), so the set is larger. The numbers are
also in `selection.json` (`size_note`).

## Dropped duplicates (section 6.1 says "embedding similarity"; no model is run here)

Strict rule, no forced count: two families are duplicates only if they share the legacy topic,
the expected behavior and the gold evidence keys AND their English required facts have Jaccard
at least 0.6 (when both have no facts: Jaccard of distinctive tokens, i.e. folded words minus
stopwords and template words, at least 0.6). Pairs are taken by descending score; a sealed family
is never dropped (its partner goes) and a family kept for one pair is never dropped later. An
earlier 5-letter-stem Jaccard dropped topic-template matches (Java vs Python, frontend vs
backend) and was replaced for that reason.

Dropped (all with identical required facts, score 1.0 unless noted):

- `language-58` (kept `language-57`): both are unsupported-input-language items answered from the same projects evidence.
- `metrics-31` (kept `rampy-mobile-startup`): both ask for the reported startup/performance numbers.
- `metrics-35` (kept `filomena-concurrency`): both ask for the 1,000+ simultaneous users and its qualifier.
- `filomena-legacy-migration` (kept `projects-12`, score 0.67): both ask what was wrong with the CakePHP and jQuery system and what the rebuild changed.

The legacy single-turn scenario `role-paraphrase` is dropped as a near-duplicate of `fit`.
An embedding-based pass can replace the lexical rule once the fixture lane has embeddings.

## Self-check (deterministic; the two-agent DR-05 review is required for golden, not here)

`tests/evals/test_full_manifest.py` asserts, for development and sealed items alike:

- schema validity (`load_items`: pydantic, unique ids and questions across both files); sealed items are loaded as `SealedItem`, whose repr is redacted, and sealed assertions use counts so a failure never prints a question;
- counts per part and locale, EN and ES within 5 (actual gap 0 overall and per part);
- sha256 per development item and the sealed file sha256, counts consistent with the manifest;
- grounding: every `required_facts` phrase occurs verbatim (folded, whole phrase) in the gold
  evidence files of its own locale or the paired locale; every `forbidden_claims` phrase is
  absent from the whole frozen corpus; answer items carry gold evidence and facts, abstain and
  refuse items carry neither (required facts and forbidden claims in development are all checked);
- no voseo in any Spanish turn (the golden regex);
- 100 legacy families accounted for: 76 development + 20 sealed + 4 dropped;
- the sealed rules below.

Spanish is written natively in neutral Latin American Spanish with tú; legacy Spanish variants
were reused where they were already native, rewritten where the legacy item mixed locale and
request language (language policy items) or used voseo (`contame`).

## Sealed holdout rules

1. The sealed wording exists only in `holdout.sealed.jsonl` (rephrased natively; it never reuses
   legacy wording). `distill_full.py --holdout-phrasing` consumed a one-off phrasing file that was
   deleted; the sealed file is now the source of truth. The tool refuses to overwrite it without
   `--force`, `--plan` never prints sealed family ids, and the 20 sealed families are pinned in
   `SEALED_FAMILIES` so the file and its hash survive changes to the duplicate screen.
2. The test module verifies the committed hash, fails if any scanned file (`prompts/` when present,
   `app/`, `evals/harness/`, `evals/golden/`, `scripts/`, `docs/`, `.claude/`, `.agents/`,
   `.codex/`, AGENTS.md, CLAUDE.md, CONTRIBUTING.md) mentions a holdout id or contains a
   normalized sealed question (only the path is printed), and checks that `sealed_aggregate` and
   `build_report(..., sealed=True)` expose counts only (cells under 5 items are suppressed; the
   `holdout` tier cannot be reported unsealed).
3. `.gitattributes` marks the file `-diff` so diffs do not display it.
4. Rotation (10 to 20% every 4 weeks of prompt work) moves replaced items to development.

## Known gaps and pending

- **No-retrieval ablation is pending**: it needs a paid live run with empty evidence; agents make
  no paid calls. Until it runs, no answer item is proven to fail without retrieval.
- Content checks are string matches (`required_facts`, `forbidden_claims`); refuse items cannot
  fail on content unless a forbidden claim matches (same limit as golden).
- `projects-15` (how the portfolio site is built) and `rampy-*` encryption and GraphRAG are
  abstain items because their facts are not in the keyed profile files (only in README or absent);
  revisit when README keys exist.
- The legacy originals `evals/assistant.json` and `evals/assistant-intents.json` stay in place
  because `scripts/`, tests and CI still read them; remove them in the PR that migrates those
  readers to `evals/archive/legacy-2026-10/` (follow-up).
