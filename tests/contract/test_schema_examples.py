"""Every committed example validates against its committed JSON Schema (offline, no app import)."""

import json

import jsonschema
import pytest

from tests.support import ROOT

CONTRACTS = ROOT / 'contracts'


def load(name):
    return json.loads((CONTRACTS / name).read_text())


def sse_events():
    examples = load('sse.examples.json')
    return [*examples['success_abstention'], examples['failure'], examples['cancelled']]


def send_message_schema():
    openapi = load('openapi.json')
    return {
        **openapi['components']['schemas']['SendMessage'],
        'components': openapi['components'],
    }


# (examples file, instances, schema). analytics-semantics.examples.json is period/country behavior
# fixtures with no schema; the unit lane asserts its semantics.
CASES = {
    'sse.examples.json': (sse_events, lambda: load('sse.schema.json')),
    'operations.example.json': (
        lambda: [load('operations.example.json')],
        lambda: load('operations.schema.json'),
    ),
    'product-analytics-v2.example.json': (
        lambda: [load('product-analytics-v2.example.json')['report']],
        lambda: load('product-analytics-v2.schema.json'),
    ),
    'product-interaction.examples.json': (
        lambda: load('product-interaction.examples.json'),
        lambda: load('product-interaction.schema.json'),
    ),
    'send-message.examples.json': (
        lambda: load('send-message.examples.json'),
        send_message_schema,
    ),
}


@pytest.mark.contract
@pytest.mark.parametrize('name', CASES)
def test_examples_validate_against_their_schema(name):
    instances, schema = CASES[name]
    schema = schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    values = instances()
    assert values, name
    for value in values:
        validator.validate(value)


@pytest.mark.contract
def test_every_examples_file_is_mapped_or_explicitly_schemaless():
    found = {path.name for path in CONTRACTS.glob('*example*.json')}
    assert found == {*CASES, 'analytics-semantics.examples.json'}
