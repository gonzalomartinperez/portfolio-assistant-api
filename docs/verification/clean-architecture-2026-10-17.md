# Clean Architecture increment · 2026-10-17

Baseline: develop `efc8855`. This increment extracts existing search cost arithmetic into
immutable `WebBudget`, moves the search-accounting port to application, injects policy at
bootstrap and narrows the legacy CLI settings exception. It adds no dependency, migration,
API/SSE change, paid call, production action or public portfolio modification.

Local WSL/Linux, frozen dependencies:

- `uv sync --frozen`: passed (Python3.14.8).
- `uv run ruff check app tests contracts scripts`: passed.
- `uv run ruff format --check app tests contracts scripts`: passed.
- `uv run mypy`: passed, 27 inner/orchestration modules.
- `uv run pytest -q -m 'not integration'`: **422 passed, 27 deselected** (16.56s).
- Final focused import-graph correction: architecture suite **23 passed**. Relative package
  reexports do not manufacture self-cycles; real absolute/relative cycles remain rejected.
- Pure pricing tests exercise invalid/nonfinite values, long-context threshold, rounding,
  maximum reservation and immutability. Adapter tests verify lock-before-reservation,
  cutoff rejection, policy-based settlement and no fabricated known usage.
- Both repository skill validation and skill-creator structural validation passed.
- Contract export produced no committed artifact drift. Known-pattern tracked/history
  secret scan found zero matches; this is not universal secret-detection proof.

Real-service/container checks remain the existing required PR CI job; no local full-stack
or new model-answer evaluation is claimed for this code-only increment. PR checks must
pass on the actual head before integration. Architecture is enforced inside the existing
offline job and its aggregate required gate; no redundant full build is added.

The static checker is not a sandbox. Five named legacy operator modules retain their
configuration default for CLI compatibility; new infrastructure modules may not inherit
that exception. See [architecture](../architecture.md) and
[coordination](../engineering-coordination.md) for exact boundaries and source references.
