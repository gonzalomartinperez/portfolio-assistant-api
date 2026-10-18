"""Completed evaluations survive later failures without repeating generation."""

import json
import os
import signal
import stat
import sys
from contextlib import contextmanager
from types import SimpleNamespace

import httpx
import pytest

from scripts import evaluate_assistant as evaluator


def prepare(monkeypatch, output):
    cases = [
        {
            'id': name,
            'question': 'Public fixture question',
            'locale': 'en',
            'split': 'development',
        }
        for name in ('first', 'second')
    ]
    monkeypatch.setattr(
        sys, 'argv', ['evaluate', '--output', str(output), '--limit', '2']
    )
    monkeypatch.setattr(evaluator, 'select_cases', lambda *args: cases)
    monkeypatch.setattr(
        evaluator,
        'configuration',
        lambda *args: SimpleNamespace(origins=['http://localhost:3000']),
    )

    @contextmanager
    def server(config):
        yield 'http://127.0.0.1:12345'

    monkeypatch.setattr(evaluator, 'evaluation_server', server)
    monkeypatch.setattr(
        evaluator.httpx,
        'get',
        lambda *args, **kwargs: httpx.Response(
            200,
            json={'corpus_version': 'fixture', 'source_commit': 'a' * 40},
            request=httpx.Request('GET', 'http://127.0.0.1:12345'),
        ),
    )


@pytest.mark.parametrize(
    'failure', [httpx.ReadTimeout('private-sentinel'), KeyboardInterrupt(), 'sigterm']
)
def test_completed_sample_is_private_and_durable_before_cleanup_and_later_interruption(
    monkeypatch,
    tmp_path,
    failure,
):
    output = tmp_path / 'report.json'
    prepare(monkeypatch, output)
    streams = []
    deletions = []
    real_client = httpx.Client

    def handle(request):
        if request.method == 'DELETE':
            snapshot = json.loads(output.read_text())
            assert snapshot['samples'][0]['id'] == 'first'
            assert stat.S_IMODE(output.stat().st_mode) == 0o600
            deletions.append(request.url.path)
            return httpx.Response(204)
        if request.url.path == '/api/v1/session':
            return httpx.Response(200, json={'csrf_token': 'synthetic'})
        if request.url.path == '/api/v1/conversations':
            return httpx.Response(200, json={'id': 'synthetic'})
        streams.append(request.url.path)
        if len(streams) == 2:
            if failure == 'sigterm':
                signal.raise_signal(signal.SIGTERM)
            raise failure
        return httpx.Response(
            200,
            text='\n'.join(
                [
                    'data: '
                    + json.dumps(
                        {
                            'type': 'message.completed',
                            'payload': {
                                'content': 'Public fixture answer',
                                'citations': [],
                            },
                        }
                    ),
                    'data: ' + json.dumps({'type': 'run.completed', 'payload': {}}),
                ]
            ),
        )

    monkeypatch.setattr(
        evaluator.httpx,
        'Client',
        lambda **kwargs: real_client(
            **kwargs,
            transport=httpx.MockTransport(handle),
        ),
    )
    previous = signal.getsignal(signal.SIGTERM)
    with pytest.raises(KeyboardInterrupt if failure == 'sigterm' else type(failure)):
        evaluator.main()
    assert signal.getsignal(signal.SIGTERM) == previous
    report = json.loads(output.read_text())
    assert report['status'] == 'interrupted'
    assert report['active_case_id'] == 'second'
    assert len(report['samples']) == 1
    assert report['samples'][0]['answer'] == 'Public fixture answer'
    assert 'private-sentinel' not in output.read_text()
    assert len(streams) == 2 and len(deletions) == 2
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


@pytest.mark.parametrize('symlink', [False, True])
def test_existing_output_is_rejected_before_any_evaluation(
    monkeypatch, tmp_path, symlink
):
    target = tmp_path / 'existing'
    target.write_text('preserve')
    output = tmp_path / 'report.json'
    if symlink:
        output.symlink_to(target)
    else:
        output.write_text('preserve')
    prepare(monkeypatch, output)

    def forbidden(*args):
        pytest.fail('an existing output reached evaluation startup')

    monkeypatch.setattr(evaluator, 'evaluation_server', forbidden)
    with pytest.raises(FileExistsError):
        evaluator.main()
    assert target.read_text() == 'preserve'
    assert output.read_text() == 'preserve'


def test_successful_completion_keeps_the_existing_sample_contract(
    monkeypatch, tmp_path
):
    output = tmp_path / 'report.json'
    prepare(monkeypatch, output)

    def complete(config, cases, url, progress):
        report = {'id': 'first', 'terminal': 'run.completed', 'human_scores': None}
        progress.start_case('first')
        progress.record(report)
        return [report]

    monkeypatch.setattr(evaluator, 'evaluate', complete)
    evaluator.main()
    report = json.loads(output.read_text())
    assert report['status'] == 'complete'
    assert report['active_case_id'] is None
    assert report['live_quality_verified'] is False
    assert report['corpus_version'] == 'fixture'
    assert report['samples'] == [
        {'id': 'first', 'terminal': 'run.completed', 'human_scores': None}
    ]


def test_size_limit_and_failed_atomic_write_preserve_previous_private_progress(
    monkeypatch, tmp_path
):
    output = tmp_path / 'report.json'
    progress = evaluator.EvaluationProgress(output, {'live_quality_verified': False})
    progress.start_case('first')
    before = output.read_bytes()
    monkeypatch.setattr(evaluator, 'MAX_REPORT_BYTES', len(before) + 10)
    with pytest.raises(ValueError, match='size limit'):
        progress.record({'answer': 'x' * 200})
    assert output.read_bytes() == before
    progress.finish('interrupted')
    assert json.loads(output.read_text())['samples'] == []
    before = output.read_bytes()

    def failed_replace(*args):
        raise OSError('synthetic write failure')

    monkeypatch.setattr(evaluator.os, 'replace', failed_replace)
    with pytest.raises(OSError):
        progress.finish('interrupted')
    assert output.read_bytes() == before
    assert list(tmp_path.iterdir()) == [output]


def test_progress_refuses_to_replace_a_foreign_report(monkeypatch, tmp_path):
    output = tmp_path / 'report.json'
    progress = evaluator.EvaluationProgress(output, {})
    foreign = tmp_path / 'foreign.json'
    foreign.write_text('preserve')
    os.replace(foreign, output)
    with pytest.raises(ValueError, match='ownership changed'):
        progress.start_case('first')
    assert output.read_text() == 'preserve'
    assert list(tmp_path.iterdir()) == [output]


def test_full_running_snapshot_always_reserves_space_for_interruption(
    monkeypatch, tmp_path
):
    output = tmp_path / 'report.json'
    progress = evaluator.EvaluationProgress(output, {})
    size = len(output.read_bytes())
    monkeypatch.setattr(evaluator, 'MAX_REPORT_BYTES', size)
    with pytest.raises(ValueError, match='size limit'):
        progress.write(progress.state)
    monkeypatch.setattr(evaluator, 'MAX_REPORT_BYTES', size + 4)
    progress.write(progress.state)
    progress.finish('interrupted')
    assert len(output.read_bytes()) == size + 4
    assert json.loads(output.read_text())['status'] == 'interrupted'
