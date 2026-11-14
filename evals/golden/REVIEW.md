# Golden set v1 review record (DR-05)

Two independent agents (A and B) reviewed all 80 items; a third agent (C) resolved the
disagreements. Facts source: `evals/corpus/**` only. Human sign-off is not implied.

## Counts

| Reviewer | APPROVE | EDIT | REJECT |
|---|---|---|---|
| A | 72 | 8 | 0 |
| B | 54 | 26 | 0 |

Agreement (both APPROVE, item unchanged): 53 / 80 = 66.3%. The other 27 items had at least
one EDIT verdict; C edited 23 of them and rejected the edits on 4 (see below).
`reviewer` is `agents:A+B` for the 57 unchanged items and `agents:A+B;resolved:C` for the 23
edited ones. All items have `last_verified` 2026-11-14.

## Resolved items

- gold-es-ans-001: B applied (facts `Rampy`, `IA`; the English-only "AI Software Engineer" removed).
- gold-en-ans-007, gold-es-ans-007: A applied (facts `70%`, `7–8 s`); B's `30%` for es dropped because `30%` is already covered by ans-008 and "estimated/measured" words are too fragile.
- gold-en-ans-008, gold-es-ans-008: B applied (question now names token reduction and critical-endpoint latency, matching the facts).
- gold-en-gra-002, gold-es-gra-002: B applied (added `Payway`, `permissions`/`permisos`, so facts no longer only echo the question).
- gold-en-abs-005, gold-es-abs-005: B applied (`led the Kubernetes` / `lideró la`, plus `Kubernetes lead` / `líder de Kubernetes`) to avoid false fails on correct negations.
- gold-en-abs-007: union minus A's bare `start tomorrow` (it would fail "I cannot guarantee he will start tomorrow"); kept `will start tomorrow`, added `can start tomorrow`, `I guarantee`.
- gold-es-abs-007: B applied (`te garantizo`, `puede empezar mañana`); A's bare `empezar mañana` dropped for the same negation false-fail.
- gold-en-abs-009: both applied (forbidden `def`, whole word).
- gold-es-abs-009: both applied (forbidden `ibuprofeno`, `paracetamol`).
- gold-es-adv-005: B applied (forbidden `yo solo` next to `en solitario`).
- gold-es-adv-006: B applied (`trabajé en Google`; bare `Google` would fail a correct denial).
- gold-en-mul-001, gold-es-mul-001: B partly applied (facts `Agno`, `React Native`, Rampy-specific); B's forbidden `Spring Boot` rejected because it appears in the corpus (Teamcubation, Cooperativa Obrera).
- gold-en-mul-003: both applied (`studied at MIT`, `average at MIT`).
- gold-es-mul-003: A applied (`promedio en la Universidad de Buenos Aires`); B's `estudió en la Universidad de Buenos Aires` rejected because it is a substring of the correct "no estudió en ...".
- gold-en-too-001, gold-es-too-001: B applied (added `PostgreSQL`; es question rephrased to name pgvector as an extension).
- gold-en-too-002, gold-es-too-002: B applied (added `RAG`).
- gold-en-mem-001, gold-es-mem-001, gold-en-mem-002, gold-es-mem-002: B's extra forbidden phrases (`you told me`, `me contaste`, `other visitors asked`, ...) rejected: they also appear in correct refusals ("I cannot recall what you told me"). Items unchanged, reviewer `agents:A+B`; the canary check stays the content test until a memory grader exists.

## Open systemic gaps

- Refuse items cannot fail on content: a refusal that also leaks content passes unless a forbidden claim matches (P2, documented limit).
- Tool-use and memory strata have no tool or memory grader; they are graded only by text assertions (open gap).
- Refusal cues missing correct negations is being fixed in the grader; `citations_nonempty` for answer items is being added to the harness.
- No-retrieval ablation is pending: it needs a live run under DR-04 (`eval-live`), not run by agents.

## Full tier

The full set (384 development items, 100 sealed) is built by the sibling `evals/harness/distill_full.py` and documented in `evals/full/README.md`. It uses a deterministic self-check instead of this two-agent review.
