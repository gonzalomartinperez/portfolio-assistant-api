"""The breaking-change gate catches planted edits (oasdiff for OpenAPI, stdlib for SSE)."""

import copy
import json
import os
import shutil

import pytest

from scripts import contract_diff
from tests.support import ROOT

OPENAPI = json.loads((ROOT / 'contracts/openapi.json').read_text())
SSE = json.loads((ROOT / 'contracts/sse.schema.json').read_text())

pytestmark = pytest.mark.contract


def need_oasdiff():
    if shutil.which('oasdiff'):
        return
    if os.environ.get('REQUIRE_OASDIFF') == '1':  # the CI contract job must never skip
        pytest.fail('oasdiff is required in CI but is not on PATH')
    pytest.skip('oasdiff not on PATH; the CI contract job installs the pinned release')


def drop_response_property(spec):
    spec['components']['schemas']['HealthView']['properties'].pop('version')
    spec['components']['schemas']['HealthView']['required'].remove('version')


def drop_endpoint(spec):
    del spec['paths']['/healthz']


def write(tmp_path, name, spec):
    path = tmp_path / name
    path.write_text(json.dumps(spec))
    return path


def test_unchanged_openapi_is_not_breaking(tmp_path):
    need_oasdiff()
    base = write(tmp_path, 'base.json', OPENAPI)
    assert contract_diff.openapi_breaking(base, base).returncode == 0


@pytest.mark.parametrize('plant', [drop_response_property, drop_endpoint])
def test_oasdiff_blocks_a_planted_breaking_edit(tmp_path, plant):
    need_oasdiff()
    head = copy.deepcopy(OPENAPI)
    plant(head)
    result = contract_diff.openapi_breaking(
        write(tmp_path, 'base.json', OPENAPI), write(tmp_path, 'head.json', head)
    )
    assert result.returncode != 0, result.stdout


def test_additive_openapi_change_is_allowed(tmp_path):
    need_oasdiff()
    head = copy.deepcopy(OPENAPI)
    head['paths']['/healthz-extra'] = copy.deepcopy(head['paths']['/healthz'])
    head['paths']['/healthz-extra']['get']['operationId'] = 'healthzExtra'
    result = contract_diff.openapi_breaking(
        write(tmp_path, 'base.json', OPENAPI), write(tmp_path, 'head.json', head)
    )
    assert result.returncode == 0, result.stdout


def run_gate(tmp_path, monkeypatch, head_openapi, head_sse, major):
    (tmp_path / 'contracts').mkdir(exist_ok=True)
    (tmp_path / 'contracts/openapi.json').write_text(json.dumps(head_openapi))
    (tmp_path / 'contracts/sse.schema.json').write_text(json.dumps(head_sse))
    base = {
        contract_diff.OPENAPI: json.dumps(OPENAPI),
        contract_diff.SSE: json.dumps(SSE),
    }
    monkeypatch.setattr(contract_diff, 'git_show', lambda sha, path: base[path])
    argv = ['--base-sha', 'base', '--head-root', str(tmp_path)]
    return contract_diff.main([*argv, '--major'] if major else argv)


def test_gate_fails_on_breaking_edit_unless_labelled_contract_major(
    tmp_path, monkeypatch
):
    need_oasdiff()
    head = copy.deepcopy(OPENAPI)
    drop_endpoint(head)
    assert run_gate(tmp_path, monkeypatch, head, SSE, major=False) == 1
    assert run_gate(tmp_path, monkeypatch, head, SSE, major=True) == 0
    assert run_gate(tmp_path, monkeypatch, OPENAPI, SSE, major=False) == 0


def test_sse_event_removal_is_breaking():
    head = copy.deepcopy(SSE)
    head['oneOf'] = [o for o in head['oneOf'] if not o['$ref'].endswith('/Cancelled')]
    assert contract_diff.sse_breaking(SSE, head) == ['SSE event removed: run.cancelled']


def test_sse_required_field_removal_is_breaking():
    head = copy.deepcopy(SSE)
    head['$defs']['Delta']['required'].remove('sequence')
    head['$defs']['DeltaPayload']['required'] = []
    problems = contract_diff.sse_breaking(SSE, head)
    assert 'SSE required field removed: message.delta.sequence' in problems
    assert 'SSE required field removed: message.delta.payload.text' in problems


def test_sse_additions_are_not_breaking():
    head = copy.deepcopy(SSE)
    head['$defs']['Ping'] = copy.deepcopy(head['$defs']['Started'])
    head['$defs']['Ping']['properties']['type']['const'] = 'run.ping'
    head['oneOf'].append({'$ref': '#/$defs/Ping'})
    head['$defs']['Delta']['required'].append('extra')
    assert contract_diff.sse_breaking(SSE, head) == []
