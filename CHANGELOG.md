# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). The version is
`[project].version` in `pyproject.toml`; see CONTRIBUTING.md for the release flow.

## [Unreleased]

### Added

- `/healthz` and `/readyz` health aliases and console-script entry points, alongside the existing forms.
- Separate `api` and `worker` container targets built with `docker-bake.hcl`, with Dockerfile lint, image
  linting, container structure tests and an image size ratchet.
- Aggregate `ci-gate` check with path-based CI profiles, shared security workflows, OpenSSF Scorecard and a
  daily vulnerability scan.
- One weekly grouped dependency pull request, enforced by a guard workflow.
- Community files (support, code of conduct, issue forms), standards drift check and release automation.

### Deprecated

- The `python -m app.migrate`, `app.retention`, `app.knowledge_sync` and `app.knowledge_watch` commands; use the
  `assistant-*` console scripts (now under `app/bootstrap/entrypoints/`). Removal waits for the vps-ops switch.

### Fixed

- Retrieval evidence keys are independent of the portfolio content layout.

## [1.0.0] - 2026-10-18

### Added

- First release of the public bilingual RAG assistant API: grounded answers with citations, PostgreSQL with
  pgvector, a Neo4j relationship projection, an atomic monthly spend cap and the versioned REST and SSE
  contract.

[Unreleased]: https://github.com/gonzalomartinperez/portfolio-assistant-api/compare/v1.0.0...develop
[1.0.0]: https://github.com/gonzalomartinperez/portfolio-assistant-api/releases/tag/v1.0.0
