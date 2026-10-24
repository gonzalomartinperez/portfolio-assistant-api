# Rubric: senior recruiter / hiring manager — public showcase (v1)

Focus from the research: how the repository reads as a public showcase in 30 seconds,
5 minutes and 30 minutes. The reviewer reads GitHub's rendered repository page, not
local files.

Total 100 points. Point allocation is the v1 proposal (see [rules](README.md)).

| Window | Criterion | Max | 95+ looks like | Baseline evidence (2026-10-24) |
|---|---|---|---|---|
| 30 s | What it is and why it matters | 15 | one-sentence hero + short streaming-with-citations media; value appears before caveats | hero is good, but the "Current state" block with 5 negations appears before any achievement |
| 30 s | Signals of seriousness | 10 | repository homepage, topics, social preview, releases, OpenSSF Scorecard badge | topics exist; homepage empty; no releases |
| 5 min | Measured results | 20 | a results table (Recall@5 EN/ES, citation support, abstention, TTFT p50/p95, cost per answer, mutation score, coverage) with date and commit | no results table; evidence spread across 46 dated reports |
| 5 min | Engineering story | 15 | "Why it's interesting" bullets linked to evidence; C4 level 1–2 diagrams; one-command demo | diagrams and gallery exist; 8-command quickstart |
| 5 min | Honest limits, briefly | 10 | one "Status & limits" paragraph with a link | 6+ paragraphs of caveats before and after the value |
| 30 min | Decisions and depth | 15 | homogeneous MADR ADRs without numbering gaps; any decision reachable in ≤ 2 clicks; Diátaxis docs map | 7 ADRs, not MADR, ADR 007 missing; 80 doc files without hierarchy |
| 30 min | Maintenance hygiene | 15 | CHANGELOG, CODEOWNERS, CODE_OF_CONDUCT, SUPPORT, issue forms, green CI, living status page separate from dated evidence | none of CHANGELOG/CODEOWNERS/CODE_OF_CONDUCT; dated evidence mixed with living docs |

Acceptance for P5 (from the research): a recruiter understands what it is, what it
demonstrates and its quality in < 60 s; a developer finds any decision in ≤ 2 clicks.

Evidence to collect per review: timed first read (30 s / 5 min / 30 min notes) of the
rendered README on the reviewed commit and the list of links followed.
