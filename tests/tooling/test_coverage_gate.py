import json

import pytest

from scripts import coverage_gate
from tests.support import ROOT

REPORT = """<?xml version="1.0" ?>
<coverage><packages><package name="x"><classes>
<class filename="domain/a.py"><lines>
<line number="1" hits="1"/>
<line number="2" hits="1" branch="true" condition-coverage="50% (1/2)"/>
</lines></class>
<class filename="app/adapters/b.py"><lines>
<line number="2" hits="1" branch="true" condition-coverage="100% (2/2)"/>
</lines></class>
<class filename="main.py"><lines>
<line number="1" hits="0" branch="true" condition-coverage="0% (0/2)"/>
</lines></class>
</classes></package></packages></coverage>
"""


@pytest.fixture
def report(tmp_path):
    path = tmp_path / 'coverage.xml'
    path.write_text(REPORT)
    return path


def test_groups_are_measured_from_branch_counts(report):
    measured = coverage_gate.measure(coverage_gate.branch_counts(report))
    assert measured['whole'] == pytest.approx(50.0)
    assert measured['domain'] == pytest.approx(50.0)
    assert measured['adapters'] == pytest.approx(100.0)
    assert measured['entrypoints'] == pytest.approx(0.0)
    assert measured['application'] == 100.0


def test_gate_passes_at_the_floor_and_fails_below(report, tmp_path):
    floors = tmp_path / 'floors.json'
    floors.write_text(json.dumps({'whole': 50.0, 'adapters': 100.0}))
    assert coverage_gate.main([str(report), '--floors', str(floors)]) == 0
    floors.write_text(json.dumps({'whole': 50.01}))
    assert coverage_gate.main([str(report), '--floors', str(floors)]) == 1
    floors.write_text(json.dumps({'nonsense': 1.0}))
    assert coverage_gate.main([str(report), '--floors', str(floors)]) == 1


def test_print_mode_does_not_gate(report, capsys):
    assert coverage_gate.main([str(report), '--print']) == 0
    assert json.loads(capsys.readouterr().out)['whole'] == 50.0


def test_committed_floors_name_known_groups():
    floors = json.loads((ROOT / 'tests/coverage-floors.json').read_text())
    assert set(floors) <= set(coverage_gate.GROUPS)
    assert {'whole', 'adapters', 'entrypoints', 'domain', 'application'} <= set(floors)
