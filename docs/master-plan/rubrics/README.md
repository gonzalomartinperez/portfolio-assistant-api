# Fixed rubrics

The owner requires 95+ on every axis, evaluated through three fixed lenses: senior
developer, senior designer (API/streaming UX) and senior recruiter (public showcase).

| Rubric | Scores |
|---|---|
| [Senior developer](senior-developer.md) | The nine engineering axes of the [scorecard](../scorecard.md) |
| [Senior designer](senior-designer.md) | The UX surfaces the API exposes: SSE, errors, messages, progress |
| [Senior recruiter](senior-recruiter.md) | How the repository reads as a public showcase in 30 s, 5 min and 30 min |

## Rules that keep the rubrics fixed

- Rubric version **v1** (2026-10-24). The lens definitions and evidence come from the
  planning research; the point allocations are this plan's proposal, open for owner
  adjustment **before** the first scored review (P0). After that review, the rubrics are
  frozen: any change bumps the version and rescores the previous baseline with the new
  version so phases stay comparable.
- Every score cites evidence: a command output, a file and line, a measured artifact or
  a screenshot. A criterion without evidence scores 0 for that criterion.
- Planned or "exists in a branch" work does not score; only what is on the reviewed
  commit counts. Fixture and live evidence are reported separately.
- A review records the commit SHA, date, rubric version, reviewer (human or agent and
  model) and the per-criterion scores. Agent reviews are labelled as such and do not
  replace the owner's judgement.
- 95+ means a strict senior reviewer in that discipline would find no material gap,
  not that every optional idea in the research is implemented.
