"""Contract docs (M5-3): described operations and schema examples that validate.

Offline and over the committed artifact only.
"""

import json

import jsonschema
import pytest

from tests.support import ROOT

pytestmark = pytest.mark.contract

OPENAPI = json.loads((ROOT / "contracts/openapi.json").read_text())
SCHEMAS = OPENAPI["components"]["schemas"]
# Framework validation shapes, a nested member, and analytics bodies whose examples live in their own
# committed files (product-interaction.examples.json, validated in test_schema_examples.py).
WITHOUT_EXAMPLES = {
    "HTTPValidationError",
    "ValidationError",
    "ProblemMessages",
    "ProductEventBody",
    "ProductInteractionBody",
}


def operations():
    return [
        (f"{method.upper()} {path}", operation)
        for path, methods in OPENAPI["paths"].items()
        for method, operation in methods.items()
    ]


@pytest.mark.parametrize(("name", "operation"), operations(), ids=[n for n, _ in operations()])
def test_every_operation_is_described(name, operation):
    assert operation.get("operationId"), name
    assert len(operation.get("description", "")) >= 30, name


def test_every_public_schema_has_examples():
    missing = sorted(
        set(SCHEMAS) - WITHOUT_EXAMPLES - {n for n, s in SCHEMAS.items() if s.get("examples")}
    )
    assert not missing


@pytest.mark.parametrize("name", sorted(n for n, s in SCHEMAS.items() if s.get("examples")))
def test_schema_examples_validate(name):
    schema = {**SCHEMAS[name], "components": OPENAPI["components"]}
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    for example in SCHEMAS[name]["examples"]:
        validator.validate(example)
