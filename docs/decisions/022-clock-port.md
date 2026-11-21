# ADR022: Clock port for wall-clock time

Status: accepted (2026-11-15, master plan task M4-3, Clock part).

## Context and problem

Eight call sites read wall-clock time directly (`datetime.now(UTC)`): session expiry in
`Conversations`, `started_at` in `RunService`, the operations snapshot (two reads) and feedback summary
timestamps, the evaluation export run time, the provider's "today" default and the SSE event
timestamp in `src/portfolio_assistant/presentation/http.py`. Tests that needed a stable "now" had to patch the
module clock or avoid asserting on time, and nothing prevented a new direct read from
appearing in `src/portfolio_assistant/application`, where policy must be deterministic.

## Decision drivers

- Deterministic tests without patching the standard library.
- Dependency direction ([ADR001](001-dependency-direction.md)): the application layer may not
  import an adapter, so the port must live in `src/portfolio_assistant/application`.
- Identical production behavior: the system UTC clock.
- A mechanical guard, because reviewers miss one-line `datetime.now()` additions.

## Considered options

1. **Inject a `Clock` port (chosen).** `src/portfolio_assistant/application/clock.py` defines the `Clock` protocol;
   `src/portfolio_assistant/adapters/clock.py` provides `SystemClock`. Consumers take a required keyword-only
   `clock: Clock` with no default.
2. **freezegun-style patching.** No production change, but it adds a dependency, patches
   global state, hides the time dependency from signatures and cannot be enforced statically.
3. **Keep direct calls.** Zero change, but time stays untestable by injection and the
   layering rule has no check for it.

## Decision outcome

Option 1. `SystemClock.now()` returns `datetime.now(UTC)` and `src/portfolio_assistant/adapters/clock.py` is the
only module in `src/portfolio_assistant/` allowed to read wall-clock time. The composition root
(`portfolio_assistant.bootstrap.container.create_app`, and `portfolio_assistant.bootstrap.evaluation_export`) creates one
`SystemClock` and passes it to `Conversations`, `RunService`, `PostgresOperations`,
`PostgresFeedback`, `ResponsesProvider` and `LangSmithEvaluationExporter`; it also sets
`app.state.clock`, which the HTTP layer reads when it stamps SSE events. `ResponsesProvider`
keeps its optional `today` override (used by cassette recording) and otherwise derives the
date from `clock.now().date()`. Monotonic timers (`perf_counter`, `monotonic`, `loop.time`)
are not wall time and are unchanged.

## Consequences

- Production behavior is unchanged; tests inject `tests.support.FixedClock`.
- Constructors gain one required keyword argument; every construction site passes it.
- Accepted residual: SQL `now()`, `CURRENT_TIMESTAMP` and `date_trunc('month', now(), ...)` in
  the PostgreSQL adapters are database time and are not controlled by the `Clock`. They
  stay as is: database time is the authority for retention windows and usage periods, and
  the integration tests exercise it against a real database.
- Timestamps compared across the two sources (for example `checked_at` stored by the
  database against `clock.now()` in `PostgresOperations.snapshot`) assume reasonably
  synchronized host and database clocks, as before.

## Confirmation

- `scripts/check_architecture.py` (`wall_clock_errors`, run by `uv run python -m
  scripts.check_architecture` and `tests/architecture/test_architecture.py::test_architecture`)
  rejects `datetime.now`, `utcnow`, `datetime.today`, `date.today`, `time.time`, `time.time_ns`,
  `time.gmtime`, `time.localtime`, `time.ctime` and `time.strftime`
  in every `src/portfolio_assistant/` module except `src/portfolio_assistant/adapters/clock.py`: calls, bare references such as
  `default_factory=datetime.now`, `datetime.datetime.now`, aliases
  (`from datetime import datetime as dt; dt.now()`, `import time as t`) and `from time import time`. It is a best-effort syntactic guard: star imports
  (`from datetime import *`) and assignment aliases (`D = datetime; D.now()`) are not tracked,
  and `getattr`, `time.clock_gettime(time.CLOCK_REALTIME)` and dynamic imports
  (`__import__("time")`) are left to review. The operator harness `evals/harness/golden.py`
  composes its own `SystemClock` in record mode; `evals/` and `scripts/` are outside the guard.
- `tests/unit/test_clock_wiring.py` proves the injected value reaches session expiry, the SSE
  timestamp and the provider's default date.
- `tests/architecture/test_architecture.py::test_rejects_wall_clock_reads` holds one negative
  probe per form; `test_allows_clock_adapter_and_monotonic_timers` proves the adapter and
  `time.perf_counter` stay allowed.
- `grep -rnE 'datetime\.now|utcnow|date\.today|datetime\.today|time\.time\(' src/portfolio_assistant` matches only
  `src/portfolio_assistant/adapters/clock.py`.
