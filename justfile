# One entry point for local verification. `just check` runs the same commands as the
# CI static job (`.github/workflows/ci.yml`); tests/harness/test_agents_commands.py
# keeps the two in step. Recipes never read `.env*` files and never call paid providers.

set shell := ["bash", "-euo", "pipefail", "-c"]

# List the recipes.
default:
    @just --list

# Install the locked environment.
sync:
    uv sync --frozen

# Static checks, identical to the CI static job (without the unit test step).
check:
    uv run python -m scripts.validate_skills
    uv run python -m scripts.check_license
    uv run ruff check app tests contracts scripts evals
    uv run ruff format --check app tests contracts scripts evals
    uv run mypy
    uv run python -m scripts.build_assistant_bank --check
    uv run python -m contracts.export && git diff --exit-code contracts

# Offline unit, contract and architecture tests (the CI static job's test step).
test:
    uv run pytest -q -m 'not integration'

# Run one test lane by name: just test-lane unit
test-lane lane:
    uv run pytest -q tests/{{lane}}

# Integration lane; needs the isolated PostgreSQL and Neo4j fixtures (docs/tutorials/local-development.md).
test-integration:
    TEST_INTEGRATION=1 uv run pytest -q -m integration

# Fixture-mode walkthrough against a running local API (no paid calls).
demo url="http://localhost:8000" locale="en":
    uv run python -m scripts.demo --url {{url}} --locale {{locale}}

# Golden eval lane: every active golden item replays from committed cassettes (record mode none).
# Needs the isolated PostgreSQL and Neo4j fixtures. Exit code 3 means "re-record required".
eval-golden:
    REQUIRE_GOLDEN_CASSETTES=1 uv run python -m evals.harness.golden

# Local scorecard: collect artifacts and check ratchets (docs/reference/scorecard.md). Slow: runs the offline suite.
score:
    mkdir -p artifacts
    uv run ruff check app tests contracts scripts --output-format json > artifacts/ruff.json || [ $? -eq 1 ]
    uv run mypy > artifacts/mypy.txt 2>&1 || [ $? -eq 1 ]
    uv run mypy --strict app > artifacts/mypy-strict-app.txt 2>&1 || [ $? -eq 1 ]
    uv run pytest -q -m 'not integration' --junitxml=artifacts/unit.xml
    uv run python -m scorecard collect --artifacts artifacts --out artifacts/scorecard.json
    uv run python -m scorecard check --current artifacts/scorecard.json --ratchets scorecard/ratchets
