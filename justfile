# One entry point for local verification. `just check` runs the same commands as the
# CI static job (`.github/workflows/ci.yml`); tests/test_agents_commands.py
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
    uv run ruff check app tests contracts scripts
    uv run ruff format --check app tests contracts scripts
    uv run mypy
    uv run python -m scripts.build_assistant_bank --check
    uv run python -m contracts.export && git diff --exit-code contracts

# Offline unit, contract and architecture tests (the CI static job's test step).
test:
    uv run pytest -q -m 'not integration'

# Integration lane; needs the isolated PostgreSQL and Neo4j fixtures (docs/local-development.md).
test-integration:
    TEST_INTEGRATION=1 uv run pytest -q -m integration

# Fixture-mode walkthrough against a running local API (no paid calls).
demo url="http://localhost:8000" locale="en":
    uv run python -m scripts.demo --url {{url}} --locale {{locale}}

# Golden eval lane (cassette replay). The golden set and replayer land in master plan M2-7.
eval-golden:
    @echo "eval-golden: the golden set and cassette replayer land in master plan M2-7" >&2
    @exit 2
