"""A trusted proxy's X-Request-ID is reused in the public shape; nobody else can set it."""

import re

import pytest
from fastapi.testclient import TestClient

from tests.support_app import build_app, pin_env

HEX = "0123456789abcdef0123456789abcdef"
UUID = "0123ABCD-4567-89ab-CDEF-0123456789ab"
PUBLIC_SHAPE = re.compile(r"[0-9a-f]{32}")


@pytest.fixture
def client_for(monkeypatch):
    pin_env(monkeypatch)

    def build(trusted: str) -> TestClient:
        return TestClient(build_app(trusted_proxy_ips=trusted))

    return build


def request_id(client: TestClient, header: str | None) -> str:
    headers = {} if header is None else {"X-Request-ID": header}
    return client.get("/healthz", headers=headers).headers["x-request-id"]


def test_trusted_proxy_hex_id_is_reused(client_for):
    assert request_id(client_for("testclient"), HEX) == HEX


def test_trusted_proxy_uuid_is_normalized_to_the_public_shape(client_for):
    assert (
        request_id(client_for("10.0.0.2, testclient"), UUID) == "0123abcd456789abcdef0123456789ab"
    )


def test_untrusted_peer_cannot_choose_the_request_id(client_for):
    issued = request_id(client_for("10.0.0.2"), HEX)
    assert issued != HEX
    assert PUBLIC_SHAPE.fullmatch(issued)


@pytest.mark.parametrize(
    "header",
    [
        "",
        HEX[:-1],
        HEX + "0",
        "g" * 32,
        HEX + "\r\nX-Injected: 1",
        "0123abcd-4567-89ab-cdef-0123456789ab-",
        "{" + UUID + "}",
    ],
)
def test_malformed_ids_from_a_trusted_proxy_get_a_fresh_id(client_for, header):
    issued = request_id(client_for("testclient"), header)
    assert PUBLIC_SHAPE.fullmatch(issued)
    assert issued not in header


def test_without_a_header_every_request_gets_its_own_id(client_for):
    client = client_for("testclient")
    first, second = request_id(client, None), request_id(client, None)
    assert first != second
    assert PUBLIC_SHAPE.fullmatch(first)


def test_problem_documents_carry_the_propagated_id(client_for):
    response = client_for("testclient").get("/api/v1/missing", headers={"X-Request-ID": HEX})
    assert response.status_code == 404
    assert response.json()["request_id"] == HEX


def test_default_configuration_trusts_no_peer(client_for):
    issued = request_id(client_for(""), HEX)
    assert issued != HEX


def test_trusted_list_tolerates_spacing_and_empty_items(client_for):
    assert request_id(client_for(" , testclient ,"), HEX) == HEX


def test_body_limit_rejections_keep_the_propagated_id_in_body_and_header(client_for):
    response = client_for("testclient").post(
        "/api/v1/analytics/events",
        content=b"x" * 2048,
        headers={"X-Request-ID": HEX, "Origin": "http://localhost:3000"},
    )
    assert response.status_code == 422
    assert response.headers["x-request-id"] == HEX
    assert response.json()["request_id"] == HEX
