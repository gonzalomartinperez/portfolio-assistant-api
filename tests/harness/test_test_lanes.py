from tests.support import ROOT

LANES = (
    'unit',
    'architecture',
    'contract',
    'evals',
    'tooling',
    'harness',
    'integration',
    'container',
    'resilience',
    'load',
)


def test_flat_test_modules_are_gone():
    assert not tuple((ROOT / 'tests').glob('test_*.py'))


def test_every_lane_is_a_package():
    assert all((ROOT / 'tests' / lane / '__init__.py').is_file() for lane in LANES)
