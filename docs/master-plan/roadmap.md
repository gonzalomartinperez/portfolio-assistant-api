# Roadmap P0–P6

**Status: planned, not scheduled.** No phase starts until the owner decides to start
it. Each phase then runs as normal task branches and PRs into `develop`; a phase's
existence here is not an authorization to merge, promote, publish images, spend on
models or deploy (see [AGENTS.md](../../AGENTS.md)).

Efforts are the research estimates for one maintainer with agent assistance. Expected
per-axis scores after each phase are in the [scorecard](scorecard.md#expected-score-by-phase).
Detailed designs are in [research/](research/).

## Activation gates

| Gate | Applies to | Condition |
|---|---|---|
| Owner start | every phase | The owner explicitly starts the phase. |
| Paid calls | P1 embeddings snapshot, P1 judge v1 runs, `eval-required` samples, P6 | Explicit authorization **and** a USD spend cap per run/campaign, recorded in the PR. |
| VPS | production activation, online canaries against the deployed service, self-hosted Langfuse, VPS-representative load numbers | The VPS is purchased and vps-ops provisions it. Until then, results are labelled local/fixture. |
| Repository settings | P0 secret scanning, push protection, CodeQL default setup, immutable releases, homepage | Owner performs or explicitly approves the setting change. |
| Image publication | GHCR push, attestations attached to a published image | Explicit approval; publication is not deployment. |

## P0 — Hygiene and quick security wins

- **Effort:** 1–2 days.
- **Scope:**
  - Secret scanning + push protection ON; CodeQL; dependency review; Scorecard.
  - Ruff: select `B`, `S`, `ASYNC`, `C90` with a per-file ignore baseline.
  - Coverage measured in CI (no gate yet) and published in the summary.
  - ADR-007 stub, initial CHANGELOG, CODEOWNERS, CODE_OF_CONDUCT, issue forms,
    repository homepage.
  - Fix README inconsistencies (uv version, "Neo4j 5.26" in the tagline vs. policy).
  - First scored review with the three [rubrics](rubrics/) to fix the designer and
    recruiter lens baselines.
- **Acceptance criteria:** Scorecard ≥ 7.5; 0 secret-scanning alerts; green CI; README
  without contradictory data.
- **Risks:** settings changes depend on the owner; a new ruff selection may surface
  findings that tempt blanket suppressions (CONTRIBUTING forbids them; use a shrinking
  per-file baseline).

## P1 — Eval foundation

- **Effort:** 1–2 weeks.
- **Scope:**
  - Qrels ≥ 150 EN/ES, harness `scripts/evaluate_retrieval.py --metrics` with ranx,
    report by locale × kind × strategy; real embeddings snapshot (authorization for
    < USD 0.01).
  - Deterministic regression suite with cassettes (60 cases) on PRs.
  - Experiments H1–H5 ([AI quality](research/ai-quality.md#weak-spot-in-english-hypotheses-and-experiments)),
    starting with per-language tsvector (additive migration).
  - Judge calibration set (≥ 120 labels) and judge v1.
- **Acceptance criteria:** holdout Recall@5 ≥ 0.95, EN–ES gap ≤ 3 pp; judge κ ≥ 0.70
  and TPR/TNR ≥ 0.90; regression 100% on PRs; numbers published in `docs/evidence/`.
- **Risks:** qrels and judge labels need owner labelling time (≥ 150 queries,
  ≥ 120 answers, a 20% double pass); the snapshot and judge runs are paid calls and
  wait for authorization and a cap.

## P2 — Architecture refactor

- **Effort:** 2–3 weeks.
- **Scope:**
  - A1 (retrieval pipeline, CC ≤ 10), A2 (domain without TS format), A3 (prompt
    registry), A4 (graph with validate), A5 (native async), A6/A7 (additive errors and
    SSE phases), A8 ([target architecture](research/architecture.md#what-changes)).
  - mypy strict across `app/` (199 → 0), extended guard.
- **Acceptance criteria:** P1 metrics without regression (± 1 pp); v1 contracts without
  breaking changes (oasdiff); ruff C901 without exceptions in `app/`; 0 `to_thread` in
  adapters; ADRs 009–015 accepted.
- **Risks:** A9 (src layout) and A5 (async) have high churn: do them in isolated PRs
  with the P1 metrics as a safety net. P2 should not start before P1 metrics exist.

## P3 — Testing depth

- **Effort:** 1–2 weeks, in parallel with P2 where applicable.
- **Scope:** the [test layout](research/testing.md#target-layout), Hypothesis (≥ 12
  properties + stateful run lifecycle), schemathesis, local testcontainers, nightly
  mutmut, Locust with TTFT.
- **Acceptance criteria:** combined branch coverage ≥ 92% with a gate; mutation domain
  ≥ 85%, application ≥ 75%, ai ≥ 70%; load test of 20 streams with p95 overhead
  ≤ 150 ms and no leaks.
- **Risks:** mutmut requires fork (Linux/WSL) and must stay within the ≤ 30 min nightly
  budget; the 2 vCPU load target is only VPS-representative once the VPS exists.

## P4 — CI/CD and supply chain

- **Effort:** 1 week.
- **Scope:** the [job graph](research/ci-cd-supply-chain.md#target-job-graph-qualityyml),
  composite action, build once, SBOM + attestations, osv-scanner, gitleaks, VEX +
  ADR-018, release-please + immutable releases.
- **Acceptance criteria:** PR wall time p95 ≤ 4 min; `gh attestation verify` OK on the
  digest; automatic CHANGELOG and release on `main`; vulnerability policy documented in
  SECURITY.md.
- **Risks:** every added tool increases surface: each enters with its ADR and its
  measured CI cost; CI gates must not be altered merely to obtain a pass
  (CONTRIBUTING).

## P5 — Showcase and docs

- **Effort:** 1 week.
- **Scope:** new README ([docs set](research/standards-docs-skills.md#docs-set)) with
  a results table, GIF and `just demo`; Diátaxis; C4; archived evidence; refactored
  skills + 4 new ones.
- **Acceptance criteria:** review with the three lenses: a recruiter understands what it
  is, what it demonstrates and its quality in < 60 s; a designer validates EN/ES error
  messages and progress phases; a developer finds any decision in ≤ 2 clicks. Skill
  scenarios pass.
- **Risks:** the results table is only as strong as the P1/P3 numbers behind it; without
  P6, live-quality rows must say "not measured live".

## P6 — Live evaluation and infrastructure decisions

- **Requires authorization and budget.** Gated by paid-call authorization with a spend
  cap; the online parts are also gated by the VPS.
- **Scope:** live capability suite (holdout 330, USD cap defined by the owner), live red
  team, pass^3, daily canaries; spike and ADR-017 Neo4j.
- **Acceptance criteria:** correct facts/abstention ≥ 95%, citation support ≥ 95%,
  language ≥ 99%, 0 critical security findings, TTFT p95 ≤ 3 s, cost p95 ≤ USD 0.005
  per answer; Neo4j decision documented with numbers.
- **Risks:** depends on spend authorizations and on the VPS; without P6, eval quality
  tops out at ~90.

## Cross-phase risks

1. P6 depends on spend authorizations and on the VPS; without P6, eval quality tops out
   at ~90, so the owner's 95+ requirement on every axis cannot be met without it.
2. A9 (src layout) and A5 (async) have high churn: isolated PRs with the P1 metrics as a
   safety net.
3. Adding tools increases surface: each one enters with its ADR and its measured CI
   cost.
