"""RFC 9457 problem documents (contract v1.1, M5-1): closed codes, EN and ES messages, wire shape."""

import ast
import json
import re

import jsonschema
import pytest
from fastapi.testclient import TestClient

from portfolio_assistant.presentation.problems import (
    CATALOG,
    ERROR_CODES,
    PROBLEM_MEDIA_TYPE,
    document,
    resolve,
)
from tests.contract.test_schemathesis import ORIGIN, build_app
from tests.support import ROOT

pytestmark = pytest.mark.contract

V1_MEMBERS = {"code", "message", "request_id"}
RFC_MEMBERS = {"type", "title", "status", "detail", "instance"}
EXTENSIONS = {"retryable", "retry_after_s", "messages"}


def error_body_validator():
    openapi = json.loads((ROOT / "contracts/openapi.json").read_text())
    schema = {**openapi["components"]["schemas"]["ErrorBody"], "components": openapi["components"]}
    return jsonschema.Draft202012Validator(schema)


def literals(node):
    """String constants a code argument can evaluate to (plain or either branch of `a if c else b`)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.IfExp):
        return literals(node.body) | literals(node.orelse)
    return set()


def raised_codes():
    """Codes passed to public error constructors.

    Covers RejectedError and HTTPException anywhere in src, and the presentation helpers
    `fail(code, ...)` and `error(request, code, ...)`.
    """
    found = set()
    for path in (ROOT / "src/portfolio_assistant").rglob("*.py"):
        presentation = "presentation" in path.parts
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            name = node.func.id
            if name == "RejectedError" and node.args:
                found |= literals(node.args[0])
            elif name == "HTTPException":
                detail = node.args[1:2] or [k.value for k in node.keywords if k.arg == "detail"]
                found |= literals(detail[0]) if detail else set()
            elif presentation and name == "fail" and node.args:
                found |= literals(node.args[0])
            elif presentation and name == "error" and len(node.args) > 1:
                found |= literals(node.args[1])
    return found


def test_catalog_matches_the_closed_code_enum():
    assert set(CATALOG) == set(ERROR_CODES)


def test_every_raised_code_is_catalogued():
    codes = raised_codes()
    assert codes, "the scan found no error codes"
    assert codes <= set(CATALOG), sorted(codes - set(CATALOG))


@pytest.mark.parametrize("code", ERROR_CODES)
def test_catalog_entry_is_complete_and_bilingual(code):
    problem = CATALOG[code]
    assert 400 <= problem.status <= 599
    assert problem.title
    assert problem.en
    assert problem.es
    assert problem.en != problem.es
    assert problem.en.endswith(".")
    assert problem.es.endswith(".")
    if problem.retry_after_s is not None:
        assert problem.retryable
        assert problem.retry_after_s >= 1
    # Neutral Latin American Spanish with "tú": no voseo or peninsular forms.
    words = set(re.findall(r"[a-záéíóúñ]+", problem.es.lower()))
    assert not words & {"vos", "probá", "intentá", "vosotros", "podéis", "tenés", "querés"}


@pytest.mark.parametrize("code", ERROR_CODES)
def test_document_validates_against_the_committed_contract(code):
    body = document(code, "a" * 32)
    error_body_validator().validate(body)
    assert set(body) == V1_MEMBERS | RFC_MEMBERS | EXTENSIONS
    assert body["type"] == f"urn:portfolio-assistant:error:{code}"
    assert body["detail"] == body["message"] == body["messages"]["en"]
    assert body["instance"] == "urn:request:" + "a" * 32


def test_unknown_codes_never_reach_the_body():
    assert resolve("Traceback: secret", 400) == "malformed_body"
    assert resolve("There was an error parsing the body", 400) == "malformed_body"
    assert resolve("Not Found", 404) == "not_found"
    assert resolve("Method Not Allowed", 405) == "method_not_allowed"
    assert resolve("anything", 418) == "invalid_request"
    assert resolve("anything", 502) == "dependency_unavailable"
    assert resolve("busy", 429) == "busy"


@pytest.fixture
def client():
    return TestClient(build_app(), headers={"Accept": PROBLEM_MEDIA_TYPE})


def test_v1_clients_keep_application_json_with_the_same_body():
    legacy = TestClient(build_app()).get("/api/v1/session")
    assert legacy.status_code == 401
    assert legacy.headers["content-type"] == "application/json"
    assert "Accept" in legacy.headers["vary"]
    assert "Origin" in legacy.headers["vary"]
    body = legacy.json()
    error_body_validator().validate(body)
    assert body["code"] == "session_required"
    assert set(body) >= V1_MEMBERS


def test_raised_status_is_preserved_and_unknown_text_dropped():
    from portfolio_assistant.presentation.problems import response

    rendered = response("I'm a teapot: internal detail", 418, "b" * 32, PROBLEM_MEDIA_TYPE)
    body = json.loads(rendered.body)
    assert rendered.status_code == body["status"] == 418
    assert body["code"] == "invalid_request"
    assert "teapot" not in rendered.body.decode()


def assert_problem(response, code, status):
    assert response.status_code == status
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    body = response.json()
    error_body_validator().validate(body)
    assert body["code"] == code
    assert body["status"] == status
    assert body["request_id"] == response.headers["x-request-id"]
    return body


def test_unknown_route_is_a_problem_document(client):
    assert_problem(client.get("/does-not-exist"), "not_found", 404)


def test_wrong_method_keeps_allow_header(client):
    response = client.put("/api/v1/session")
    assert_problem(response, "method_not_allowed", 405)
    assert "POST" in response.headers["allow"]


def test_malformed_json_is_a_validation_problem(client):
    response = client.post(
        "/api/v1/conversations",
        content=b"{not json",
        headers={"Origin": ORIGIN, "Content-Type": "application/json"},
    )
    body = assert_problem(response, "invalid_request", 422)
    assert "not json" not in json.dumps(body)


def test_validation_error_never_echoes_input(client):
    response = client.post(
        "/api/v1/analytics/events",
        json={"schema_version": 1, "event_name": "<script>marker</script>"},
        headers={"Origin": ORIGIN},
    )
    body = assert_problem(response, "invalid_request", 422)
    assert "marker" not in json.dumps(body)


def test_origin_denied_and_rejected_errors_share_the_shape(client):
    assert_problem(client.post("/api/v1/session"), "origin_denied", 403)
    assert_problem(client.get("/api/v1/session"), "session_required", 401)


def test_retry_after_header_matches_the_member(client):
    response = client.post(
        "/api/v1/session",
        json={},
        headers={"Origin": ORIGIN, "X-Session-Bootstrap": "1"},
    )
    body = assert_problem(response, "rate_limited", 429)
    assert body["retryable"] is True
    assert response.headers["retry-after"] == str(body["retry_after_s"]) == "3600"


def test_every_documented_error_offers_problem_json():
    openapi = json.loads((ROOT / "contracts/openapi.json").read_text())
    missing = [
        f"{method.upper()} {path} {status}"
        for path, operations in openapi["paths"].items()
        for method, operation in operations.items()
        for status, response in operation["responses"].items()
        if int(status) >= 400 and PROBLEM_MEDIA_TYPE not in response.get("content", {})
    ]
    assert not missing


def body_limit_call(receive, accept=PROBLEM_MEDIA_TYPE, maximum=32, timeout=10.0):
    import asyncio

    from portfolio_assistant.presentation.middleware import BodyLimit

    sent = []

    async def app(scope, receive, send):  # pragma: no cover - must not be reached
        raise AssertionError("the guarded app was invoked")

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/x",
        "headers": [(b"accept", accept.encode())],
    }
    asyncio.run(BodyLimit(app, maximum=maximum, timeout=timeout)(scope, receive, send))
    headers = {name.decode(): value.decode() for name, value in sent[0]["headers"]}
    return sent[0]["status"], headers, json.loads(sent[1]["body"])


def test_body_limit_oversize_is_a_problem_document():
    async def receive():
        return {"type": "http.request", "body": b"a" * 64, "more_body": False}

    status, headers, body = body_limit_call(receive)
    assert status == 422
    assert body["code"] == "invalid_request"
    assert headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert headers["x-request-id"] == body["request_id"]
    error_body_validator().validate(body)
    assert "aaaa" not in json.dumps(body)


def test_body_limit_timeout_is_a_retryable_problem_document():
    import asyncio

    async def receive():
        await asyncio.sleep(1)
        return {"type": "http.request", "body": b"", "more_body": False}

    status, headers, body = body_limit_call(receive, accept="application/json", timeout=0.01)
    assert status == 408
    assert body["code"] == "request_timeout"
    assert body["retryable"] is True
    assert headers["content-type"] == "application/json"
    assert headers["cache-control"] == "no-store"
    assert headers["x-request-id"] == body["request_id"]
    error_body_validator().validate(body)


def test_openapi_override_is_idempotent():
    app = build_app()
    first = app.openapi()
    assert app.openapi() is first
    responses = first["paths"]["/healthz"]["get"]["responses"]
    assert PROBLEM_MEDIA_TYPE in responses["422"]["content"]


def test_middleware_statuses_are_documented_on_body_routes():
    """The origin guard (403) and the body guard (408) can answer every POST, PATCH and DELETE."""
    openapi = json.loads((ROOT / "contracts/openapi.json").read_text())
    missing = [
        f"{method.upper()} {path} {status}"
        for path, operations in openapi["paths"].items()
        for method, operation in operations.items()
        if method in ("post", "patch", "delete")
        for status in ("403", "408")
        if status not in operation["responses"]
    ]
    assert not missing
