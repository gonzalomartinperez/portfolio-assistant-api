# Master plan v2: portfolio-assistant-api

Dated 2026-11-09. Baseline: `origin/develop` `e749ca762fb3f1e74225d9126d4eb1bbd88e2885`. **Planning only: this folder starts nothing by itself; execution is gated by the milestones of [roadmap.md](roadmap.md). DR-04 pre-authorizes the embeddings snapshot, cassette recording, judge runs and live pass^3 within its caps (USD 2 per campaign, USD 8 per month, separate key, `eval-live` environment); only exceeding a cap needs the owner. Deploys, image publication and production changes stay with the owner (DR-13).** The ecosystem standard ([ecosystem.md](ecosystem.md)) governs; this plan applies it to this repository and documents only justified deviations.

## 1. Purpose

Bring the portfolio's RAG assistant API from a rigorous but unmeasured fixture-mode service (baseline: strong architecture and tests, but no measured answer quality, 199 strict-typing errors, 77.6% coverage, a 992 MB image, a stale golden retrieval dataset) to a 95-on-every-axis service whose quality **cannot silently degrade**: a golden set that must pass 100% before any release, a larger full set that reports per-family and per-language metrics, deterministic graders first, ratchets, an automatic scorecard, dynamic CI and a weekly single dependency PR.

## 2. Owner requirements (verbatim from the ecosystem standard, section 2.1)

1. Nine master plans, one per repo (seven originally; `pequeverso-marketing` and `dropshipping-ops` were added the same day), polished to the maximum, grounded in deep 2025-2026 research.
2. "Perpetual excellence": quality does not degrade over time (ratchets, automatic scorecard, cadences).
3. Consistent READMEs across the nine repos.
4. Assistants: a golden set of RAG questions, 100% correct as release gate.
5. Complete testing: unit, integration, mutation, E2E, contract, visual, a11y, performance, security, load, property-based.
6. Agentic harness (skills, reviewers, evals) good enough that the owner does not need to review code.
7. Use the available skills and harness.
8. First-class, consistent containers: LTS versions, same base configuration, same practices.
9. CI at the maximum: dynamic (runs only what is affected), secure, fast.
10. Dependabot identical in all nine: exactly one PR per week per repo (section 5).
11. Maximum redesign of both backoffices (designer quality, unique UI/UX, shared view/IA standard, per-project identity).
12. Master UI/UX on both public sites (keep identity, polish and elevate, strict performance and accessibility budgets; Pequeverso prioritizes conversion).

Repo-specific requirements and decisions (owner, 2026-11-09, from `owner-decisions.md`):

- Pragmatism: rigor where it reduces real risk, no ceremony.
- Two eval tiers: (1) golden set (40 to 80 items, 100% gate, cassette replay on every PR that touches assistant quality, live run before release); (2) full set (existing corpus cleaned and versioned, on demand, per-family and per-language metrics, no 100% gate, real failures promoted to golden). Portfolio targets: full set about 450 bilingual items with about 100 holdout, golden about 80. Full-set goals: Recall@5 of at least 0.90 per family, EN-ES gap of at most 3 pp, critical invariants 100%, judged quality of at least 95% with a validated judge.
- Quality must not degrade over time: ratchets, automatic scorecard, cadences.
- Paid model calls are pre-authorized within the DR-04 caps; labels are bootstrapped by agents (DR-05) with one owner spot check; only the VPS (D7 floor 90 until MV) and that spot check (P3 provisional floor 90) still gate an axis.
- Public repository: nothing private, no secrets, no raw model answers committed.

## 3. Method

Read-only audit of `origin/develop` (export, `uv sync --frozen`, fixture mode, no key, no paid call), 2026-11-09, evidence in [audit.md](audit.md) and [audit/](audit/). Plan assembled from the ecosystem standard, the shared research notes (cited by number, copied into [research/](research/); notes 14 and 15 cover the Codex and Claude Code harness), the v1 plan on `main` (kept where still right) and the repository's own rules (`AGENTS.md`, `CONTRIBUTING.md`, ADRs). Evidence labels: measured, read, hypothesis. Axis scores marked "judged" are planner estimates until the independent evaluator agent scores them at M3 (rubric rule: evaluators never see the planner's reasoning).

## 4. Headline baseline (rubrics v2, no averaging across axes)

| Lens | Axes (baseline) |
|---|---|
| Senior developer | D1 Architecture 82, D2 Code quality 58, D3 Tests 66, D4 CI/CD 70, D5 Security 68, D6 Performance 62, D7 Observability 72, D8 Docs and DX 64 |
| Senior designer (API and conversational UX) | P1 78, P2 80, P3 assistant message quality 50, P4 80, P5 74, P6 70 |
| Senior recruiter | 66 |

Targets: 95 everywhere; floor 90 for D7 until the VPS exists (MV); P3 is 95 and drops to a provisional 90 only until the owner's 20% spot check of the judge labels is done. See [scorecard.md](scorecard.md).

Top findings (details and evidence in [audit.md](audit.md)): P0-1 the golden retrieval data still points at the portfolio's retired `src/content` layout (hybrid 2 of 9 on the current layout, 8 of 9 on the old); P0-2 a real abstention failure hides behind it; P0-4 Dependabot opens several PRs; P0-5 BuildKit cache id copied from vps-ops; P0-6 the holdout is not sealed; P1-1 `mypy --strict app` has 199 errors and the configured scope covers 39 of 95 files; P1-2 retrieval `search` has complexity 48; P1-4 coverage 77.6% line and 68.7% branch with adapters weakest; P1-7 one inline unversioned prompt; P1-8 image 992 MB versus 368 MB for the sibling.

## 5. Decisions

Status: **Decided** (made by this plan, reversible by the owner through an ADR) or **Resolved (delegated)** (was an owner question; the recommendation in section 7 was adopted under the standing delegation).

| ID | Decision | Why | Sources | Alternatives rejected | Status |
|---|---|---|---|---|---|
| PAA-D1 | Two eval tiers: golden 80 (gate 100%, cassette on PR, live pass^3 before release) and full 450 (100 sealed holdout, reported not gated); legacy 1,000 + 40 bank archived after distillation | Owner decision; a single readable regression set plus an on-demand discovery set | ecosystem 12.0 to 12.1; [03] section 16; `owner-decisions.md` | Several parallel suites (owner rejected); keeping the 1,000-case bank as a gate (3 of 5 variations are format variants, never answer-reviewed) | Decided |
| PAA-D2 | Frozen in-repo snapshot of the approved public corpus for CI and evals, refreshed by explicit PR | Removes two cross-repo checkouts, gives deterministic evals and a stable `corpus_snapshot_id`; invariant 1 (no cross-repo dependency at runtime) | [05] 2.2; audit P1-9 | Keep the pinned checkout (flaky across layout moves, network dependency in every PR) | Resolved (delegated, 2026-11-09) (was an owner question: rights) |
| PAA-D3 | Layout-neutral canonical evidence keys `<locale>/<topic>[#entity]` used by qrels, golden and citations comparison | Root cause of P0-1 is path coupling to the portfolio layout | audit P0-1; roadmap M1-1; `docs/coordination/portfolio-content-layout.md` | Updating the 9 paths by hand (breaks again at the next layout move) | Decided |
| PAA-D4 | Retrieval harness with ranx, Recall@5 primary; two lanes (offline fixture lane; frozen real-embedding snapshot lane) | 5 sources reach the generator; CI embeddings are hashes | ecosystem 12.3; [03] section 4; ranx | Hand-coded metrics; always-live embeddings | Resolved (delegated, 2026-11-09) (was an owner question: spend below USD 0.01, hypothesis) |
| PAA-D5 | Judge limited to two binary criteria, different model family, validated against 160 labels bootstrapped by two independent agents with a 20% owner spot check (DR-05), outside every gate until validated | One binary criterion per judge; safety is deterministic | ecosystem 12.3; [03] section 7 | General "quality" judge; RAGAS or DeepEval as gate | Resolved (delegated, 2026-11-09) (was an owner question: labels, judge spend) |
| PAA-D6 | Cassettes at the provider port keyed by prompt, model and evidence | Weekly SDK bumps break HTTP cassettes; key makes prompt changes visible | [03] section 14; ecosystem 12.3 | `vcrpy` HTTP cassettes for the gate (kept for transport tests) | Decided (deviation S3) |
| PAA-D7 | Prompts in git with front matter and `prompts.lock`; `prompt_version` recorded everywhere | Tie quality to a prompt change; privacy forbids hosted tracing | ecosystem 12.3; [03] section 12 | LangSmith prompt hub; inline strings | Decided |
| PAA-D8 | Tracing stays off; no hosted dataset or prompt registry now | Existing settings validator encodes the privacy decision | `app/bootstrap/config.py`; [03] section 13 | Mirror golden to LangSmith (ecosystem default; deviation S5) | Decided |
| PAA-D9 | Eval spend caps: USD 2 per campaign, USD 8 per month, separate provider key and project, `eval-live` environment with no required reviewer (controls: branch restriction, the code-level DR-04 hard stop, separate provider key) | Estimated campaign cost is cents at configured prices; a cap bounds mistakes | ecosystem E11; assistant-quality.md section 12 | Production key for evals; no cap | Resolved (delegated, 2026-11-09) (was an owner question: spend) |
| PAA-D10 | `src/portfolio_assistant` layout, package rename `app` to `portfolio_assistant`, one isolated mechanical PR at M4 | Ecosystem 10.2; generic top-level `app` name | [02] section 6 | Keep `app/` (generic name; ecosystem template for all nine repos) | Decided (veto window) |
| PAA-D11 | Image targets `api` (no git) and `worker`; size budget at most 500 MB, ratcheted; measure the `lingua` share first | 992 MB versus 368 MB; git needed only by the worker | audit P1-8; ecosystem 8.2 | Single image (status quo); distroless (Python venv complications) | Decided |
| PAA-D12 | Keep Neo4j until a one-day spike measures graph marginal Recall@5 per kind | v1 left ADR-017 open; fleet standard pins Neo4j 5.26 LTS | [03] section 5; ecosystem 8.1 | Remove now (no data); keep forever (vendor findings, extra container) | Resolved (delegated, 2026-11-09) (was an owner question: after M6 spike) |
| PAA-D13 | Skills canonical in `.agents/skills`, `.claude/skills` symlinks; existing 5 skills mapped into the standard catalog | Ecosystem 15.1, 15.5; Claude Code reads only `.claude/skills`, Codex only `.agents/skills` | [08] section 4, [14], [15] | Keep inverted layout | Decided |
| PAA-D14 | Retire `dependency-policy.yml` and Dependabot automation scripts; adopt the weekly single-PR rule and shared guard | Owner rule O1 and O8 (manual merge, one PR); `pull_request_target` class forbidden | ecosystem 5 and 6.4; `shared/dependabot-rule.md` | Keep auto-merge policy (conflicts with owner rule) | Decided |
| PAA-D15 | First release 1.1.0 at M7; the image is built with SBOM and provenance and kept as a CI artifact; GHCR publication and deploy stay disabled until MV (DR-13) | Publication is not deployment; additive contract change is a minor | ecosystem 3.2, 7; [05] section 6 | Publish earlier; major version (nothing breaks) | Resolved (delegated, 2026-11-09) (was an owner question: owner) |
| PAA-D16 | Sealed holdout of about 100 lives in the full tier, re-drawn from never-referenced variants; golden has no sealed part | 66 of 330 old holdout IDs are exposed; regression items must be readable | audit P0-6; ecosystem 12.1 | Seal 30% of golden (cannot be fixed when it fails) | Decided (deviation S4) |
| PAA-D17 | Contract v1.1 additive: RFC 9457 problems, opt-in `run.progress`, `/healthz` and `/readyz` | Actionable errors and progress without breaking v1 | ecosystem 3.3, 8.5, 10.2 | Breaking redesign; parallel `/v2`; no change | Decided |
| PAA-D18 | Retrieval pipeline with RRF k = 60, declarative ablatable rules, per-language text-search experiment, reranker only if Recall@5 stays below 0.90 | Complexity 48 and overfit boosts; measurable per rule | v1 A1; [03] section 4 | Local cross-encoder (500 MB, no evidence) | Decided |
| PAA-D19 | mutmut 3 after a Python 3.14 spike; fallback mewt or muton | Ecosystem 11.2; unverified on 3.14 | [04] section 3.2 | cosmic-ray | Decided (spike) |
| PAA-D20 | No shared runtime package with pequeverso-assistant-api now; scaffolding from `engineering-standards` templates | Premature coupling; invariant 1 | [02] section 13 | `assistant-kit` package (revisit at three identical modules) | Resolved (delegated, 2026-11-09) (was an owner question: cross-repo, low urgency) |
| PAA-D21 | Keep layer names `ai` and `presentation`, ports under `application/ports/` | 394-file churn for no behaviour gain; guard already encodes the rule | [02] section 2.2 | Rename to ecosystem names | Decided (deviation S1) |

## 6. Limits

- Baseline is one commit on one day; later commits change numbers.
- Judged axes are estimates until M3; automatic axes follow the rubric rules mechanically.
- Costs are estimates at the repository's configured prices, unverified against the provider (about 0.001 USD per answer).
- mutmut on Python 3.14, Dependabot grouped-PR behaviour, `lingua` share of the image and the Neo4j marginal gain are hypotheses to be measured in named spikes.
- No live, VPS or production verification was performed; P3 is provisional at 90 until the owner's 20% spot check of judge labels, D7 floor is 90 until MV; both are stated in [scorecard.md](scorecard.md) section 4. Declined nice-to-haves: none (all applied; judge calibration heavy parts moved to M6-3).
- Licence and health columns of [dependencies.md](dependencies.md) are knowledge-based and are corrected by M1-10.
- Agent-hours are estimates; milestone and total effort equal the sums of the roadmap rows (total 522 h, critical path about 159 h, see [roadmap.md](roadmap.md)).
- Merges are merge commits, never squash (RESUME section 6).

## 7. Decision log (delegated resolutions) and the owner inputs

| ID | Question | Recommendation |
|---|---|---|
| PAA-D2 | May approved public portfolio content (about 76 chunks) be committed under `evals/corpus/`? | Resolved (delegated, 2026-11-09): yes, commit the approved public portfolio content (about 76 chunks) under `evals/corpus/`; it is already public; keep `THIRD_PARTY_NOTICES` scope text; fallback is the pinned checkout |
| PAA-D4 | Authorize the one-off embeddings snapshot (estimated under USD 0.01)? | Resolved (delegated, 2026-11-09): yes, one-off embeddings snapshot at the start of M2 with a USD 0.05 cap (within the DR-04 caps) |
| PAA-D5 | Who labels 160 judge-calibration items (40 pass and 40 fail for two criteria), and which judge model family and spend? (answered by DR-05 and DR-04) | Resolved (delegated, 2026-11-09): per DR-05 the planner bootstraps the 160 judge-calibration labels with two independent agents; the owner spot-checks a 20% sample once; judge from a non-OpenAI family under the DR-04 cap; until validated no judged metric gates anything (release gates use deterministic graders) |
| PAA-D9 | Approve spend caps and the separate key (USD 2 per campaign, USD 8 per month)? | Resolved (delegated, 2026-11-09): yes; caps USD 2 per campaign and USD 8 per month (DR-04) with a separate key; one recording campaign at M2 and one live pass^3 at M6 |
| PAA-D10 | Any objection to the `src` rename at M4? | Resolved (delegated, 2026-11-09): no objection; the `src` rename proceeds at M4 |
| PAA-D12 | Neo4j or PostgreSQL graph? | Resolved (delegated, 2026-11-09): decided by spike per DR-10: run the Neo4j vs PostgreSQL graph spike in M4 (recorded in ADR 0018 and re-checked with the M6 full-set numbers); keep Neo4j if multi-hop Recall@5 gains at least 5 points |
| PAA-D15 | Publish the image to GHCR at M7? | Resolved (delegated, 2026-11-09): no image publication to GHCR at M7 (DR-13): the release-candidate image is built with SBOM and provenance and kept as a CI artifact (MV-R); registry publication and deploy are activated by the owner in one step at MV |
| PAA-D20 | Shared runtime package with the sibling API? | Resolved (delegated, 2026-11-09): not now |
| E1 to E14 | Ecosystem decisions | Resolved (delegated, 2026-11-09): as recommended in `ecosystem.md` section 19 (DR-03, DR-09, DR-10, DR-12 apply) |

### Owner inputs still needed (exactly three; identical in README, RESUME and progress)

1. PAA-D5: one-time spot check of a 20% sample of the bootstrapped judge labels (DR-05); P3 stays at its provisional floor of 90 until it is done.
2. Release approvals: the M7 promotion `develop` to `main` and the one-time GitHub settings checklist of M1-8 (toggles no agent can set); unset toggles never block work, the dependent scorecard criterion stays unmet.
3. MV: VPS purchase and activation authorization (OD-64; owner steps are purchase, DNS and secret entry only).

## 8. Changes from v1 (the plan on `main`, 2026-10-24)

Kept: six layers, AST guard and `Protocol` ports without a DI framework; retrieval pipeline with standard RRF and ablatable rules; domain free of portfolio format; prompt registry with hash; per-language text-search experiment; judge calibration discipline; Locust for SSE load; Hypothesis and mutmut on the core layers; release-please with immutable releases; README of at most 250 lines with a measured-results table; Diataxis, MADR and C4; additive error and SSE v1.1; rejected Pact, DeepEval or RAGAS as gate, local reranker, Phoenix.

Changed:

- Phases P0 to P6 became ecosystem milestones M0 to M8 and MV (MV-R inside M6), each a safe point with a tag and progress log; efforts are now per item in agent-hours with parallel streams (v1 gap 7).
- Ten weighted axes became rubrics v2 (three lenses, no averaging, caps); the weighted 72 is retired and replaced by per-axis baselines (v1 gap 2).
- The eval design was simplified by owner decision: from regression, capability, red-team and language suites plus about 150 qrels, 120 judge labels (v1) and sampled live PR evals, to **two tiers** (golden 80 at 100% and full 450 with sealed holdout), 160 judge labels for two criteria (agent-bootstrapped, 20% owner spot check), no live evals on PRs. Recall@5 target moved from 0.95 holdout to 0.90 per family with an EN-ES gap of at most 3 pp, as the owner set.
- Added: the P0 stale golden data finding (hybrid 2 of 9 on the current layout), the holdout exposure (66 of 330), frozen corpus snapshot, canonical keys, provider-port cassettes, spend caps and floors, `psycopg` licence exception, image split and size budget, `Clock` port, health aliases, cross-repo contract jobs, skills layout inversion and activation evals, scorecard tooling with ratchet files (v1 gaps 1, 3, 4, 5).
- Retired: the privileged dependency-policy automation and scripts (owner rule of one manually merged weekly PR), `IMPLEMENTATION_STATUS.md` and `docs/work-checklist.md` volatile status, the generated 1,000-case bank as a quality gate, daily canaries and live PR samples (moved to Phase V and release only).
- Decided what v1 left open: `src/` layout (yes, M4), ADR-017 Neo4j (spike at M6, now ADR 0018), eval PR samples (cassette instead).
- Drift fixed: v1 counted 866 tests (still true: 819 offline plus 47 integration); the audit SHA moved from `44ae6c7` to `e749ca7`.

## 9. Index

| File | Contents |
|---|---|
| [README.md](README.md) | This file |
| [scorecard.md](scorecard.md) | Baselines, targets, floors, automatic measurement, ratchets, cadence |
| [rubrics.md](rubrics.md) | Ecosystem rubrics v2 (byte-identical) |
| [audit.md](audit.md), [audit/](audit/) | Measured baseline and findings P0 to P2 |
| [target-state.md](target-state.md) | Architecture, guards, typing, retrieval refactor, contract v1.1, ADR list |
| [assistant-quality.md](assistant-quality.md) | Two eval tiers, graders, judge, retrieval harness, guardrails, prompts, budgets, cassettes |
| [assistant-experience.md](assistant-experience.md) | Assistant experience v2: performance, grounding, rich blocks contract, web access policy, opt-in memory, harness, evals, rollout |
| [testing.md](testing.md) | Lanes, thresholds, every row of the test catalog |
| [ci-cd.md](ci-cd.md) | Profiles, `ci-profile.json`, containers, supply chain, Dependabot, release |
| [file-index.csv](file-index.csv), [file-moves.md](file-moves.md) | Every tracked file with destination; every move with motive |
| [standards.md](standards.md) | Style and enforcement, explicit deviations |
| [docs-and-community.md](docs-and-community.md) | README outline, Diataxis, community files |
| [skills.md](skills.md) | Skills audit, new skills, activation evals, review chain |
| [dependencies.md](dependencies.md) | Dependency table and decisions |
| [roadmap.md](roadmap.md) | M0 to M8 and MV checklists (MV-R inside M6) |
| [ecosystem.md](ecosystem.md) | Ecosystem standard (byte-identical) |
| [owner-decisions.md](owner-decisions.md), [owner-decisions-existing.md](owner-decisions-existing.md), [readme-template.md](readme-template.md) | Owner decisions register, decisions taken before 2026-11-09, README template (byte-identical copies) |
| [progress.md](progress.md), [RESUME.md](RESUME.md) | Milestone log and in-flight tasks; session-independent resume brief with the resume command |
| [research/](research/), [sources.md](sources.md) | Cited research notes and external sources |
