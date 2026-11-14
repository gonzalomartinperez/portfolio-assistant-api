# Security baseline, 2026-11-14

Task M1-7 (security workflows). Fixture and offline evidence only; no live service was contacted except the
public Scorecard API.

## zizmor

Command: `uvx zizmor@1.30.1 --offline --min-severity medium .github/workflows`

| State | Findings reported | High | Medium |
| --- | --- | --- | --- |
| Before (develop, `ci.yml` and `dependency-policy.yml`) | 3 | 3 | 0 |
| After (this change, four workflow files) | 1 | 1 | 0 |

Before: two `cache-poisoning` findings (`docker/setup-buildx-action` binary cache in the `database` and `container` jobs)
and one `dangerous-triggers` finding (`pull_request_target` in `dependency-policy.yml`).

After: the buildx steps set `cache-binary: false`, and the `container` job no longer enables the `setup-uv` cache (it
exports Docker layers, which zizmor treats as a publishing step). The only remaining finding is `dependency-policy.yml`
`pull_request_target`, which the parallel M1-6 change removes. The new `scorecard.yml` and `vuln-daily.yml` add none.

## OpenSSF Scorecard

`https://api.securityscorecards.dev/projects/github.com/gonzalomartinperez/portfolio-assistant-api` returned HTTP 404:
there is no public score yet. The first scheduled or `main` push run of `scorecard.yml` publishes results and sets the
baseline.

## CodeQL

Not configured. Enabling default setup (`actions`, `python`) is an owner toggle tracked in
docs/reference/repo-settings.md.
