"""A completed HTTP request is not a successful conversation evaluation."""

import json
from contextlib import nullcontext

import httpx
import pytest

from scripts import evaluate_conversations


def test_failed_terminal_writes_report_cleans_session_and_exits_nonzero(
    monkeypatch, tmp_path
):
    deleted = []

    def respond(request):
        if request.method == 'DELETE':
            deleted.append(request.url.path)
            return httpx.Response(204)
        if request.url.path.endswith('/session'):
            return httpx.Response(200, json={'csrf_token': 'fixture'})
        if request.url.path.endswith('/conversations'):
            return httpx.Response(200, json={'id': 'fixture'})
        return httpx.Response(
            200,
            text='data: {"type":"run.failed","payload":{"code":"generation_failed"}}\n\n',
        )

    client_class = httpx.Client
    monkeypatch.setattr(
        evaluate_conversations,
        'fixture_server',
        lambda: nullcontext('https://fixture.test'),
    )
    monkeypatch.setattr(
        evaluate_conversations.httpx,
        'Client',
        lambda **kwargs: client_class(**kwargs, transport=httpx.MockTransport(respond)),
    )
    monkeypatch.setattr(
        evaluate_conversations, 'SCENARIOS', {'overview': ['A fixture question']}
    )
    report = tmp_path / 'failed.json'
    monkeypatch.setattr('sys.argv', ['evaluate_conversations', '--output', str(report)])
    with pytest.raises(SystemExit, match='failed or incomplete'):
        evaluate_conversations.main()
    data = json.loads(report.read_text())
    assert data['samples'][0]['terminal'] == 'run.failed'
    assert data['samples'][0]['answer'] is None
    assert deleted == ['/api/v1/session']
