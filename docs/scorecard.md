# Scorecard tooling

The `scorecard/` package (stdlib only, not copied into the runtime image because `.dockerignore`
excludes everything not named by a Dockerfile) turns CI artifacts into `artifacts/scorecard.json` and
enforces ratchets. engineering-standards v1.0.0 has no scorecard tooling, so it lives here and may move to
the shared package later. Design: [master-plan/scorecard.md](master-plan/scorecard.md) section 5.

## Run it

```bash
just score    # ruff and mypy outputs, offline tests with junit, collect, check (slow)
uv run python -m scorecard collect --artifacts artifacts --out artifacts/scorecard.json
uv run python -m scorecard check --current artifacts/scorecard.json --ratchets scorecard/ratchets
uv run python -m scorecard tighten --current artifacts/scorecard.json --ratchets scorecard/ratchets
```

Inputs in `artifacts/` (each optional): `ruff.json` (`ruff check --output-format json`), `mypy.txt`,
`unit.xml` and `integration.xml` (junit), `coverage.xml`, `mutation.json` (`{"score": 0.0}` placeholder),
`image-sizes.json` (`{"api_bytes": 0, "worker_bytes": 0}`), `golden.json` (`{"passed": 0, "total": 0}`).
Judged axes come from the latest `docs/evidence/scores/<date>.md`, else `not yet scored`.

A missing input is recorded as `null` with status `missing`, and its criterion is `unmet`, never `pass`.
Criteria without a collector yet (most of D1, D4, D5, D7, D8) are listed as `unmet`.

## Ratchets

`scorecard/ratchets/*.json` declare, per metric, a `direction` (`lower` or `higher` is better), a `value`
(`null` means not yet measurable; the `source` note says why) and optionally a `pointer` to another file
(`image.json` points at `infra/docker/app/image.json`, which stays the owner of the size ratchet).
`check` exits 1 when a metric is worse than its ratchet and prints a table; `unmet` and `unseeded` rows do
not fail unless `--strict` is given. `tighten` rewrites a ratchet only when the measured value is better
(or seeds a `null`), never the other way. Loosening a ratchet needs an ADR and the owner.

## Nightly

`.github/workflows/nightly.yml` (cron `0 6 * * *`, 03:00 ART, plus manual dispatch) runs ruff, mypy and the
offline suite, collects, uploads `scorecard.json` as the `scorecard` artifact (30 days; numbers only, in line
with the artifact privacy boundary in [ci.md](ci.md)) and fails the job on a regression.
