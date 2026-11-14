"""Golden lane: every active golden item through the runner with recorded cassettes.

``python -m evals.harness.golden`` replays (record mode ``none``) and exits 0 on a full
pass, 1 on failing items and 3 when a cassette is missing. ``--record`` runs the same
lane through ``RecordingCassetteProvider`` (paid; refused unless ``EVAL_RECORDING=1`` and
``EVAL_ENVIRONMENT=eval-live`` are set, in addition to ``ALLOW_PAID_AI`` and a budget).
Nothing here reads ``.env*``; the OpenAI key is read from the process environment only
in record mode.
"""

import argparse
import asyncio
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.application.contracts import Provider
from app.bootstrap.config import Settings
from evals.harness.cassettes import (
    CASSETTE_DATE,
    CASSETTE_ROOT,
    EXIT_RE_RECORD,
    LEDGER_PATH,
    RE_RECORD_MESSAGE,
    CassetteConfig,
    RecordingCassetteProvider,
    RecordingRefusedError,
    ReplayProvider,
    SpendCapError,
    recording_enabled,
)
from evals.harness.items import Item
from evals.harness.loader import load_items
from evals.harness.report import ItemOutcome, build_report
from evals.harness.result import GradingContext
from evals.harness.runner import run_items

GOLDEN_PATH = Path('evals/golden/golden.jsonl')


def golden_items(path: Path = GOLDEN_PATH) -> list[Item]:
    return [item for item in load_items(path) if item.status == 'active']


def has_cassettes(root: Path = CASSETTE_ROOT) -> bool:
    return any(root.glob('*/*.jsonl'))


def lane_settings() -> Settings:
    """Fixture-mode settings (the app only accepts a provider override there)."""
    return Settings(
        _env_file=None,  # type: ignore[call-arg]  # pydantic-settings init kwarg
        ai_provider='fixture',
        embeddings_provider='fixture',
        allow_paid_ai=False,
        openai_api_key=None,
    )


def failing_by_stratum(outcomes: list[ItemOutcome]) -> dict[str, list[str]]:
    report = build_report(outcomes, tier='golden', run_id='local')
    failing = report['failing_ids_by_stratum']
    assert isinstance(failing, dict)
    return failing


async def run_golden(
    provider: Provider, config: Settings, items: list[Item]
) -> list[ItemOutcome]:
    return await run_items(items, config, provider, ctx=GradingContext())


def _record(args: argparse.Namespace, config: Settings) -> int:
    if not recording_enabled():
        print(
            'recording refused: set EVAL_RECORDING=1 and EVAL_ENVIRONMENT=eval-live',
            file=sys.stderr,
        )
        return 4
    from app.adapters.providers.answer import ResponsesProvider
    from app.adapters.providers.http import create_async_client
    from app.adapters.providers.language import LocalLanguageDetector

    if args.scope != 'golden':
        print(
            'only --scope golden exists until the full set (M2-8) is frozen',
            file=sys.stderr,
        )
        return 2

    async def campaign() -> int:
        try:
            budget = (
                Decimal(args.campaign_budget_usd)
                if args.campaign_budget_usd is not None
                else None
            )
        except InvalidOperation:
            print('invalid --campaign-budget-usd', file=sys.stderr)
            return 2
        cassette = CassetteConfig(CASSETTE_ROOT, config.openai_model)
        allowed = os.environ.get('ALLOW_PAID_AI', '').lower() == 'true'
        client = await create_async_client(api_key=os.environ.get('OPENAI_API_KEY'))
        try:
            inner = ResponsesProvider(
                client,
                config.openai_model,
                LocalLanguageDetector().rejects_output,
                web_search=None,
                today=lambda: CASSETTE_DATE,
            )
            recorder = RecordingCassetteProvider(
                inner,
                cassette,
                allow_paid_ai=allowed,
                campaign_budget_usd=budget,
                input_usd_per_million=Decimal(config.input_usd_per_million),
                output_usd_per_million=Decimal(config.output_usd_per_million),
                ledger_path=LEDGER_PATH,
            )
            outcomes = await run_golden(recorder, config, golden_items())
        finally:
            await client.close()
        print(
            f'recorded {len(recorder.recorded)} cassettes, estimated USD {recorder.spent:.6f}'
        )
        return _finish(outcomes)

    try:
        return asyncio.run(campaign())
    except (RecordingRefusedError, SpendCapError) as error:
        print(f'recording stopped: {error}', file=sys.stderr)
        return 4


def _finish(outcomes: list[ItemOutcome]) -> int:
    failing = failing_by_stratum(outcomes)
    for stratum, ids in failing.items():
        print(f'FAIL {stratum}: {", ".join(ids)}', file=sys.stderr)
    return 1 if failing else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--campaign-budget-usd')
    parser.add_argument('--scope', choices=('golden', 'full'), default='golden')
    args = parser.parse_args(argv)
    config = lane_settings()
    if args.record:
        return _record(args, config)
    if not has_cassettes():
        print(RE_RECORD_MESSAGE, file=sys.stderr)
        return EXIT_RE_RECORD
    replay = ReplayProvider(CassetteConfig(CASSETTE_ROOT, config.openai_model))
    outcomes = asyncio.run(run_golden(replay, config, golden_items()))
    if replay.missing:
        print(RE_RECORD_MESSAGE, file=sys.stderr)
        return EXIT_RE_RECORD
    return _finish(outcomes)


if __name__ == '__main__':
    raise SystemExit(main())
