# Contributing

Developed and maintained exclusively by Gonzalo Martin Perez. Suggestions, bug reports
and constructive feedback are welcome through the repository’s available channels.
Development priorities, implementation, reviews and releases remain the maintainer’s
responsibility. Security reports use the private channel in [SECURITY.md](SECURITY.md).

Start with the [local fixture guide](docs/local-development.md),
[architecture](docs/architecture.md) and [acceptance checklist](docs/release-checklist.md).
Use a task branch and PR into `develop`. Preserve the public v1 contract and add
behavior tests for changed risk. Do not introduce private portfolio material or
credentials. `AGENTS.md` is the canonical agent guidance.

## Python conventions

The [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
is our reference, adapted to Python 3.14, typed application contracts and Ruff:

- Ruff owns formatting: four-space indentation, its 88-column wrapping target,
  single-quoted strings, and triple-double-quoted docstrings. Long SQL and URLs
  may exceed the wrapping target. Do not hand-format against the formatter.
- Use absolute imports and explicit names. Importing types/functions directly is
  allowed when their source is clear; no wildcard imports or mutable global
  clients. Keep imports grouped by Ruff's import sorter.
- Use `snake_case` functions/modules, `PascalCase` classes and descriptive names.
  Prefer `list[T]`, `T | None`, `collections.abc` and typed `Protocol` ports.
- Public contracts and operationally sensitive methods need concise docstrings.
  Explain invariants, ownership, cancellation, failure behavior or non-obvious
  units. Use Google `Args:`, `Returns:`, `Yields:` and `Raises:` sections when they
  add information; do not restate obvious type annotations or narrate code.
- Use immutable dataclasses for inner value objects and Pydantic at transport/
  configuration boundaries. Avoid mutable defaults, hidden I/O and import-time
  connections. Context managers own resources and transactions.
- Catch specific expected exceptions. Broad catches are allowed only at explicit
  public/framework fault boundaries with a local explanation and safe translation.
  Never swallow cancellation or include provider/DB exception text in responses.
- Keep comments for reasons and constraints. Prefer small cohesive functions;
  do not build generic frameworks to satisfy style rules.

Ruff replaces Google's suggested pylint/formatter combination; mypy enforces
strict typing in domain, application and AI orchestration. SDK-shaped dynamic
values stay at framework adapters, with explicit translation into typed contracts.
There are no blanket type exclusions. Expanding strict coverage must address real
adapter contracts rather than adding `Any` or suppressions to silence errors.
Ruff's Google docstring convention validates the docstrings we write; review checks
whether their content explains the public behavior. Formatting, linting, typing
and architecture checks run in CI. Local rule suppressions require a specific
reason; whole-rule/file blanket suppressions are not an accepted shortcut.

## Checks and PRs

```sh
uv sync --frozen
uv run ruff check app tests contracts scripts
uv run ruff format --check app tests contracts scripts
uv run mypy
uv run pytest -q
uv run python -m contracts.export
git diff --exit-code contracts/openapi.json contracts/sse.schema.json
```

Run the documented real-service suite for persistence, retrieval, session or
streaming changes. CI also builds and smokes the production container. Include
what changed, why, tests actually run and remaining limits in each PR. Keep
migration history immutable. Do not alter CI gates merely to obtain a pass.

## Legal and security

Application software and first-party engineering documentation use the standard
[MIT license](LICENSE). Keep its grant/copyright notice intact and run
`uv run python -m scripts.check_license` when editing licensing metadata.
Personal content, identity assets and dependencies are separate; see
[third-party notices](THIRD_PARTY_NOTICES.md) for scope/attribution and
[SECURITY.md](SECURITY.md) for private vulnerability reporting.

## Agent skills

See [repository skills](docs/agent-skills.md) for Codex/Claude discovery, invocation,
authority boundaries, maintenance and compatibility evidence. Validate catalog
changes with `uv run python -m scripts.validate_skills`; CI uses the same command.

Dependency maintenance follows [the conservative Dependabot policy](docs/dependency-updates.md).
Passing CI alone does not qualify a dependency update. Review scope, transitive
changes and activation/required-check state before enabling any automated path.

Application and fixture checks use Python 3.14.8 from the frozen uv environment.
Use uv 0.13.1: older uv 0.12.10 download metadata cannot provision the pinned
interpreter on a clean checkout. CI and the Docker builder use the same reviewed
uv version; no global tool installation or lockfile regeneration is required.
Privileged stdlib-only dependency/release scripts also support runner Python 3.12;
Ruff per-file targets and a grammar test preserve that security boundary.

Support and upgrade decisions: [supported-version policy](docs/support-policy.md). Python3.14.8 remains the verified runtime; PostgreSQL18 uses a separate data volume.

For private operational changes, preserve the scalar-only application observation
model and server-to-server authentication boundary. Run the focused observability
tests plus real-store tests when modifying SQL. Review actual OTLP receiver payloads,
not only mock exporter calls; never add automatic SDK input/output capture.

## Architectural review

Use Microsoft's dependency-inversion guidance and Google/Microsoft review practices as
references, with [explicit repository adaptations](docs/engineering-coordination.md).
Application/domain rules belong behind owned ports; composition injects concrete adapters.
Review invariants, cancellation and transaction ownership rather than folder names.
`uv run python -m scripts.check_architecture` provides fast standalone feedback; normal
`uv run pytest -q` includes both the guard and its negative regression probes in CI.
Adding a layer exception requires a concrete compatibility reason, focused tests and an
architecture documentation update. Do not broaden an allowlist to silence a violation.

Use the owner name exactly as **Gonzalo Martin Perez** in both languages; do not
remove accents from other Spanish text or rewrite historical evidence.
