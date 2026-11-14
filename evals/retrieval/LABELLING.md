# Retrieval relevance labelling guideline

Input: `qrels.candidates.jsonl`. Each line is one query with its candidate evidence keys
(`<locale>/<topic>`, for locales `en` and `es` and topics `profile`, `experience`,
`projects`, `education`) and a PROPOSED relevance. The proposal is a hint derived from the
golden `gold_evidence_ids` (`proposal_basis: gold_evidence_ids`), the legacy retrieval
qrels (`legacy_qrels`) or only the legacy question topic (`topic_hint`, the weakest). It is
not a label: decide from the question and the frozen corpus (`evals/corpus/`), then confirm
or overturn it.

Output (one file per labeller, same format, JSONL): `{"query_id", "key", "relevance"}` for
EVERY candidate pair, relevance 0, 1 or 2. Label independently: labeller A and labeller B
must not see each other's files. A third labeller sees only the pairs on which A and B
disagree and writes the resolution file in the same format (an optional `rationale` field
is ignored). `uv run python -m evals.harness.qrels_resolve --a A.jsonl --b B.jsonl
--resolution C.jsonl --out evals/retrieval/qrels.jsonl --stats evals/retrieval/qrels.stats.json`
writes `qrels.jsonl` and the agreement statistics (agreement rate, Cohen's kappa).

## Scale

- **2 (essential)**: the document holds the facts needed to answer the question (a required
  fact, or the entity the question names). A grounded answer cannot be written without it.
  Several keys can be 2 when the question needs all of them (for example "which roles share
  technologies with Filomena" needs the project and the experience documents).
- **1 (supporting)**: the document is on topic and a grader would accept it as an additional
  citation (context, a corroborating mention, the second half of a comparison that the
  essential document already answers), but the answer does not depend on it.
- **0 (not relevant)**: anything else, including documents that merely share generic words
  ("Gonzalo", "experience") with the question.

## Rules

1. Judge the content of the key in the corpus, not its name. Open the file when unsure.
2. Locale: the assistant answers in the request locale (`locale` in `queries.jsonl`), so
   keys of the OTHER locale are 0 even when they hold the same facts. Cross-locale
   evidence is not penalized in the product, and measuring it is ablation H4, not a label.
   This also applies to the cross-lingual stratum (question text in one language, request
   locale in the other): relevance follows the request locale.
3. No-answer queries (`expects_evidence: false`: employer or school not in the corpus,
   private data, out of scope, hiring promises, an ambiguous or gibberish query): every
   candidate is 0, unless the corpus really contains the answer, in which case flag the
   query in your notes so the query set can be corrected.
4. False premises ("Is Kubernetes leadership documented?"): label what lets the assistant
   check the claim (the experience document is 2), not what would confirm it.
5. Entity-level anchors (`<key>#<entity>`) are not labelled yet: keys are topic documents.
   Chunk-level and entity-level qrels are a follow-up.
6. A label of 2 needs a quotable passage; when the only link is thematic, use 1.
7. Do not use any model answer, rubric, `required_facts` of other items, or the sealed
   holdout; use the question, the corpus, and this guideline only.

## Disagreement resolution

The third labeller picks the final value for each disputed pair applying these rules in the
same order, and may add a one-line `rationale`. Disagreements between 1 and 2 about a
document holding the named entity resolve to 2; between 0 and 1 about a merely thematic
document resolve to 0.

## Labelling record (2026-11-14, DR-05 model, no owner review)

- Labeller A saw the proposed relevance as a hint (this guideline). Labeller B was told to
  ignore the proposal fields and judged only question against corpus. Neither saw the
  other's file. The resolver C saw only the 37 disputed pairs, not either labeller's value.
- Result (`qrels.stats.json`): 1216 pairs, agreement 0.9696, Cohen's kappa 0.904 (binary
  0.932), 37 disagreements over 35 queries resolved by C. Because A saw the proposal,
  agreement is partly anchored on it through A only; B was independent of it.
