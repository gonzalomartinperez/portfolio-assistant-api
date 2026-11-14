"""Golden lane (integration): every active golden item replays from cassettes at 100%.

Until the recording campaign has happened there are no cassettes. With
``REQUIRE_GOLDEN_CASSETTES=1`` (``just eval-golden``) that fails loudly with the re-record
message; otherwise the test skips with an explicit reason.
"""

import asyncio
import os

import pytest

from evals.harness.cassettes import (
    CASSETTE_ROOT,
    RE_RECORD_MESSAGE,
    CassetteConfig,
    ReplayProvider,
)
from evals.harness.golden import (
    failing_by_stratum,
    golden_items,
    has_cassettes,
    lane_settings,
    main,
    recording_enabled,
    run_golden,
)

REQUIRED = os.getenv('REQUIRE_GOLDEN_CASSETTES') == '1'
PENDING = (
    'golden cassettes not recorded yet: recording campaign pending (DR-04, eval-live)'
)


def cassettes_missing() -> None:
    if REQUIRED:
        pytest.fail(RE_RECORD_MESSAGE, pytrace=False)
    pytest.skip(PENDING)


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv('TEST_INTEGRATION') != '1' and not REQUIRED,
    reason='isolated stores required',
)
def test_every_active_golden_item_passes_from_cassettes():
    if not has_cassettes():
        cassettes_missing()
    config = lane_settings()
    replay = ReplayProvider(CassetteConfig(CASSETTE_ROOT, config.openai_model))
    outcomes = asyncio.run(run_golden(replay, config, golden_items()))
    # Partial misses are drift (a prompt or evidence change): always a failure.
    if replay.missing:
        pytest.fail(RE_RECORD_MESSAGE, pytrace=False)
    failing = failing_by_stratum(outcomes)
    assert not failing, f'failing golden items by stratum: {failing}'
    assert outcomes


def test_recording_is_refused_without_the_explicit_flags(monkeypatch, capsys):
    monkeypatch.delenv('EVAL_RECORDING', raising=False)
    monkeypatch.delenv('EVAL_ENVIRONMENT', raising=False)
    assert not recording_enabled()
    assert not recording_enabled({'EVAL_RECORDING': '1'})
    assert not recording_enabled({'EVAL_ENVIRONMENT': 'eval-live'})
    assert recording_enabled({'EVAL_RECORDING': '1', 'EVAL_ENVIRONMENT': 'eval-live'})
    assert main(['--record', '--campaign-budget-usd', '1']) == 4
    assert 'recording refused' in capsys.readouterr().err
