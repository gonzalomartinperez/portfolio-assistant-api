# Contributing

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

Public visibility is not an open-source license. No source license has been
selected; the owner must decide before granting reuse rights. See
[third-party notices](THIRD_PARTY_NOTICES.md) for dependency attribution and
[SECURITY.md](SECURITY.md) for private vulnerability reporting.

## Agent skills

See [repository skills](docs/agent-skills.md) for Codex/Claude discovery, invocation,
authority boundaries, maintenance and compatibility evidence. Validate catalog
changes with `uv run python -m scripts.validate_skills`; CI uses the same command.

Dependency maintenance follows [the conservative Dependabot policy](docs/dependency-updates.md).
Passing CI alone does not qualify a dependency update. Review scope, transitive
changes and activation/required-check state before enabling any automated path.

Application and fixture checks use Python 3.14 from the frozen uv environment.
Privileged stdlib-only dependency/release scripts also support runner Python 3.12;
Ruff per-file targets and a grammar test preserve that security boundary.
