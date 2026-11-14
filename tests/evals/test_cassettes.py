"""Cassette key, replay (record mode none) and the DR-04 recording hard stop; fake inner only."""

import asyncio
import json
import stat
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from app.adapters.providers.answer import assemble_request
from app.application.contracts import Usage
from evals.harness import cassettes
from evals.harness.cassettes import (
    RE_RECORD_MESSAGE,
    CassetteConfig,
    CassetteFormatError,
    CassetteMissingError,
    RecordingCassetteProvider,
    RecordingRefusedError,
    ReplayProvider,
    SpendCapError,
    build_request,
    cassette_key,
    cassette_path,
    prompt_slug,
)

EVIDENCE = (
    'PUBLIC SOURCE [1] content/en/education.ts lines 1-5:\nUniversidad Nacional del Sur'
)
VERSION = 'answer@1+abc'
DEFAULT = Usage(0, 0)


class FakeInner:
    def __init__(self, usage: Usage | None = DEFAULT, fail=False):
        self.calls = 0
        self.usage = Usage(1000, 100, VERSION) if usage is DEFAULT else usage
        self.fail = fail

    async def stream(self, question, evidence, locale, history=(), context=None):
        self.calls += 1
        yield 'Gonzalo studied '
        yield 'at UNS [1].'
        if self.fail:
            raise RuntimeError('boom')
        if self.usage:
            yield self.usage


def collect(provider, question='Where did he study?', evidence=EVIDENCE, locale='en'):
    async def run():
        return [item async for item in provider.stream(question, evidence, locale)]

    return asyncio.run(run())


@pytest.fixture(autouse=True)
def campaign_flags(monkeypatch):
    monkeypatch.setenv('EVAL_RECORDING', '1')
    monkeypatch.setenv('EVAL_ENVIRONMENT', 'eval-live')


@pytest.fixture
def config(tmp_path):
    return CassetteConfig(tmp_path / 'cassettes', 'gpt-6-luna')


@pytest.fixture
def ledger(tmp_path):
    path = tmp_path / 'ledger.json'
    path.write_text('{}')
    return path


def recorder(config, ledger, inner=None, **overrides):
    options = {
        'allow_paid_ai': True,
        'campaign_budget_usd': Decimal('1.00'),
        'input_usd_per_million': Decimal('0.10'),
        'output_usd_per_million': Decimal('0.50'),
        'ledger_path': ledger,
        'clock': lambda: __import__('datetime').date(2026, 11, 14),
    }
    return RecordingCassetteProvider(
        inner or FakeInner(), config, **{**options, **overrides}
    )


def request_for(config, question='Where did he study?', evidence=EVIDENCE, locale='en'):
    return build_request(question, evidence, locale, (), None, config)


def test_key_covers_prompt_model_effort_limit_and_evidence(config):
    base = cassette_key(request_for(config), config)
    assert base == cassette_key(request_for(config), config)
    assert len(base) == 64
    changed = {
        'model': cassette_key(request_for(config), replace(config, model='other')),
        'effort': cassette_key(
            request_for(config), replace(config, reasoning_effort='high')
        ),
        'limit': cassette_key(
            request_for(config), replace(config, max_output_tokens=10)
        ),
        'evidence': cassette_key(request_for(config, evidence=EVIDENCE + ' x'), config),
        'question': cassette_key(request_for(config, question='Other?'), config),
        'locale': cassette_key(request_for(config, locale='es'), config),
    }
    assert base not in changed.values()
    assert len(set(changed.values())) == len(changed)


def test_key_changes_with_the_prompt_version_and_pinned_date(config):
    first = request_for(config)
    other_date = replace(config, today=config.today.replace(day=15))
    assert cassette_key(first, config) != cassette_key(
        request_for(other_date), other_date
    )
    forged = replace(first, prompt_version='answer@2+zzz')
    assert cassette_key(first, config) != cassette_key(forged, config)


def test_request_is_the_one_the_real_provider_assembles(config):
    from app.adapters.providers.answer import visitor_inputs

    question, history = visitor_inputs('Where did he study?', ())
    expected = assemble_request(
        question, EVIDENCE, 'en', history, None, None, config.today
    )
    assert request_for(config) == expected
    assert request_for(config).messages[0]['role'] == 'developer'
    assert (
        json.loads(request_for(config).messages[1]['content'])['public_evidence']
        == EVIDENCE
    )


def test_slug_is_a_safe_single_path_component():
    assert prompt_slug('answer@1+b4f38ad5eabb,voice-en@1+0123') == (
        'answer@1+b4f38ad5eabb_voice-en@1+0123'
    )
    assert '/' not in prompt_slug('../../etc/passwd')
    assert not prompt_slug('..').startswith('.')


def test_replay_missing_key_raises_and_is_remembered(config):
    replay = ReplayProvider(config)
    with pytest.raises(CassetteMissingError) as error:
        collect(replay)
    assert RE_RECORD_MESSAGE in str(error.value)
    assert replay.missing == [error.value.key]
    assert cassettes.EXIT_RE_RECORD == 3


def test_empty_evidence_needs_no_cassette(config):
    items = collect(ReplayProvider(config), evidence='')
    assert items and all(isinstance(i, str) for i in items)


def test_record_then_replay_is_identical_and_incremental(config, ledger):
    inner = FakeInner()
    rec = recorder(config, ledger, inner)
    first = collect(rec)
    assert first == ['Gonzalo studied ', 'at UNS [1].', Usage(1000, 100, VERSION)]
    assert inner.calls == 1 and len(rec.recorded) == 1
    assert collect(rec) == first  # existing key: replayed, not re-recorded
    assert inner.calls == 1
    assert collect(ReplayProvider(config)) == first
    request = request_for(config)
    path = cassette_path(config.root, request, cassette_key(request, config))
    assert path.is_file()
    assert stat.S_IMODE(path.stat().st_mode) & 0o022 == 0
    text = path.read_text()
    rows = [json.loads(line) for line in text.splitlines()]
    assert [r['type'] for r in rows] == ['meta', 'delta', 'delta', 'usage']
    for banned in ('authorization', 'api_key', 'sk-', 'Bearer', 'headers'):
        assert banned.lower() not in text.lower()


def test_corrupt_cassette_is_rejected(config, ledger):
    request = request_for(config)
    key = cassette_key(request, config)
    path = cassette_path(config.root, request, key)
    path.parent.mkdir(parents=True)
    path.write_text('{"type":"delta","text":"x"}\n')
    with pytest.raises(CassetteFormatError):
        collect(ReplayProvider(config))
    path.write_text('{"type":"meta","key":"other"}\n')
    with pytest.raises(CassetteFormatError):
        collect(ReplayProvider(config))


@pytest.mark.parametrize(
    ('allow', 'budget'),
    [
        (False, Decimal('1.00')),
        (True, None),
        (True, Decimal(0)),
        (True, Decimal(-1)),
        (True, Decimal('2.01')),
        (True, Decimal('NaN')),
    ],
)
def test_recording_refuses_without_authorization_and_a_capped_budget(
    config, ledger, allow, budget
):
    with pytest.raises(RecordingRefusedError):
        recorder(config, ledger, allow_paid_ai=allow, campaign_budget_usd=budget)


def test_recording_accepts_the_cap_itself(config, ledger):
    recorder(config, ledger, campaign_budget_usd=Decimal('2.00'))


def test_recording_refuses_a_missing_or_invalid_ledger(config, tmp_path):
    with pytest.raises(RecordingRefusedError):
        recorder(config, tmp_path / 'absent.json')
    bad = tmp_path / 'bad.json'
    for text in ('[]', '{"2026-11": "x"}', '{"nov": "1"}', '{"2026-11": "-1"}'):
        bad.write_text(text)
        with pytest.raises(RecordingRefusedError):
            recorder(config, bad)


def test_spend_is_charged_from_usage_and_persisted(config, ledger):
    rec = recorder(config, ledger, FakeInner(Usage(1_000_000, 1_000_000, VERSION)))
    collect(rec)
    assert rec.spent == Decimal('0.60')
    assert cassettes.load_ledger(ledger) == {'2026-11': Decimal('0.60')}


def test_campaign_cap_hard_stops_before_the_call(config, ledger):
    inner = FakeInner()
    rec = recorder(config, ledger, inner, campaign_budget_usd=Decimal('0.0001'))
    with pytest.raises(SpendCapError):
        collect(rec)
    assert inner.calls == 0
    assert rec.spent == 0
    assert not list(config.root.glob('*/*.jsonl'))


def test_second_call_stops_when_the_remaining_campaign_budget_cannot_cover_it(
    config, ledger
):
    inner = FakeInner(None)  # no usage: charged the worst case
    probe = recorder(config, ledger)
    reserve = probe.worst_case(request_for(config))
    rec = recorder(config, ledger, inner, campaign_budget_usd=reserve * Decimal('1.5'))
    collect(rec)
    with pytest.raises(SpendCapError):
        collect(rec, question='A different question?')
    assert inner.calls == 1


def test_monthly_cap_reads_the_committed_ledger(config, ledger):
    ledger.write_text('{"2026-11": "7.999999"}')
    inner = FakeInner()
    with pytest.raises(SpendCapError):
        collect(recorder(config, ledger, inner))
    assert inner.calls == 0
    ledger.write_text('{"2026-10": "7.999999"}')  # another month does not count
    collect(recorder(config, ledger, inner))
    assert inner.calls == 1


def test_missing_usage_is_charged_at_the_worst_case_and_still_recorded(config, ledger):
    rec = recorder(config, ledger, FakeInner(usage=None))
    collect(rec)
    assert rec.spent == rec.worst_case(request_for(config)) > 0


def test_failed_stream_is_charged_and_writes_no_cassette(config, ledger):
    rec = recorder(config, ledger, FakeInner(fail=True))
    with pytest.raises(RuntimeError):
        collect(rec)
    assert rec.spent > 0
    assert not list(config.root.glob('*/*.jsonl'))
    assert rec.recorded == []


def test_committed_ledger_is_valid_and_empty_or_under_the_cap():
    ledger = cassettes.load_ledger(Path('evals/cassettes/spend-ledger.json'))
    assert all(total <= cassettes.MONTHLY_CAP_USD for total in ledger.values())


def test_recorder_refuses_without_the_campaign_flags(config, ledger, monkeypatch):
    monkeypatch.delenv('EVAL_RECORDING')
    with pytest.raises(RecordingRefusedError, match='EVAL_RECORDING'):
        recorder(config, ledger)


@pytest.mark.parametrize('price', [Decimal(0), Decimal('-0.1'), Decimal('NaN')])
def test_recorder_refuses_prices_that_would_disable_the_caps(config, ledger, price):
    with pytest.raises(RecordingRefusedError, match='prices'):
        recorder(config, ledger, output_usd_per_million=price)


def test_recorder_refuses_a_config_that_misdescribes_the_request(config, ledger):
    with pytest.raises(RecordingRefusedError, match='does not describe'):
        recorder(replace(config, reasoning_effort='high'), ledger)


def test_ledger_rounds_charges_up(tmp_path):
    path = tmp_path / 'ledger.json'
    cassettes.save_ledger(path, {'2026-11': Decimal('0.0000001')})
    assert json.loads(path.read_text()) == {'2026-11': '0.000001'}
