"""Characterization of Settings.safe_configuration: messages, order and accepted shapes."""

import pytest
from pydantic import ValidationError

from portfolio_assistant.bootstrap.config import Settings

PRICING = {
    "input_usd_per_million": "0.10",
    "output_usd_per_million": "0.50",
    "reservation_usd": "0.05",
}
PROD_BASE = {
    "environment": "production",
    "secure_cookies": True,
    "allowed_origins": "https://example.org",
    "database_url": "postgresql://app:secret@db.internal:5432/app",
    "neo4j_password": "a-real-password",
    "neo4j_uri": "bolt://graph.internal:7687",
    "rate_hash_key": "k" * 32,
}
OTEL_BASE = {
    "otel_sdk_disabled": False,
    "ops_read_token": "t" * 32,
    "ops_api_commit": "a" * 40,
}
OPENAI = {"ai_provider": "openai", "allow_paid_ai": True, "openai_api_key": "k"}
PROD_OPENAI = {
    **PROD_BASE,
    **OPENAI,
    "embeddings_provider": "openai",
    "require_fresh_knowledge": True,
    **PRICING,
}


def build(**values: object) -> Settings:
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def rejected(message: str, **values: object) -> None:
    with pytest.raises(ValidationError) as caught:
        build(**values)
    assert message in str(caught.value)


def test_default_and_full_production_configurations_are_accepted():
    assert build().environment == "development"
    assert build(**PROD_OPENAI).environment == "production"
    assert build(**PROD_BASE).secure_cookies


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (
            {"product_analytics_country_enabled": True},
            "country attribution requires explicitly trusted proxy addresses",
        ),
        ({"langsmith_tracing": True}, "external tracing is disabled for this application"),
        ({"langchain_tracing_v2": True}, "external tracing is disabled for this application"),
        ({"langchain_tracing": True}, "external tracing is disabled for this application"),
        ({"langsmith_tracing_v2": True}, "external tracing is disabled for this application"),
        (
            {"ops_read_token": "t" * 32},
            "operational access requires an identified API revision",
        ),
        (
            {"otel_sdk_disabled": False},
            "telemetry requires private endpoint and operational configuration",
        ),
        (
            {
                "otel_sdk_disabled": False,
                "ops_read_token": "t" * 32,
                "ops_api_commit": "a" * 40,
            },
            "telemetry requires private endpoint and operational configuration",
        ),
        (
            {"web_search_enabled": True},
            "web search requires explicitly authorized OpenAI",
        ),
        (
            {"web_search_enabled": True, "ai_provider": "openai", "openai_api_key": "k"},
            "web search requires explicitly authorized OpenAI",
        ),
        ({"web_search_usd_per_call": "0.009"}, "web search price must cover the reviewed fee"),
        ({"monthly_budget_usd": "10.01"}, "monthly budget must not exceed the approved USD 10"),
        ({"embedding_usd_per_million": "0"}, "embedding price must be finite and positive"),
        (
            {"embeddings_provider": "openai"},
            "OpenAI embeddings require explicit paid authorization",
        ),
        (
            {"embeddings_provider": "openai", "ai_provider": "openai", "allow_paid_ai": True},
            "OpenAI embeddings require explicit paid authorization",
        ),
        (
            {"knowledge_freshness_seconds": 60, "knowledge_poll_seconds": 60},
            "freshness interval must exceed polling interval",
        ),
        (
            {"ai_provider": "openai", "openai_api_key": "k"},
            "paid provider requires explicit provider, allowance and key",
        ),
        (
            {"ai_provider": "openai", "allow_paid_ai": True},
            "paid provider requires explicit provider, allowance and key",
        ),
        ({"allow_paid_ai": True}, "paid allowance requires the OpenAI provider"),
    ],
)
def test_non_production_validations_report_exact_messages(values, message):
    rejected(message, **values)


def test_budget_value_object_still_validates_pricing_inputs():
    with pytest.raises(ValidationError):
        build(reservation_usd="0", monthly_budget_usd="1.00", reserve_cutoff_usd="1.00")


def test_first_failing_validation_is_reported_first():
    rejected(
        "external tracing is disabled",
        product_analytics_country_enabled=False,
        langsmith_tracing=True,
        ops_read_token="t" * 32,
        web_search_enabled=True,
    )
    rejected(
        "operational access requires an identified API revision",
        ops_read_token="t" * 32,
        otel_sdk_disabled=False,
        web_search_enabled=True,
    )
    rejected(
        "web search requires explicitly authorized OpenAI",
        web_search_enabled=True,
        web_search_usd_per_call="0.001",
        monthly_budget_usd="11",
    )
    rejected(
        "web search price must cover the reviewed fee",
        web_search_usd_per_call="0.001",
        monthly_budget_usd="11",
    )
    rejected(
        "monthly budget must not exceed",
        monthly_budget_usd="11",
        embedding_usd_per_million="0",
    )
    rejected(
        "OpenAI embeddings require",
        embeddings_provider="openai",
        knowledge_freshness_seconds=40,
        knowledge_poll_seconds=40,
    )
    rejected(
        "freshness interval must exceed",
        knowledge_freshness_seconds=40,
        knowledge_poll_seconds=40,
        allow_paid_ai=True,
    )
    rejected(
        "paid provider requires",
        ai_provider="openai",
        allow_paid_ai=False,
        environment="production",
    )


def test_telemetry_requires_both_token_and_endpoint():
    rejected(
        "telemetry requires private endpoint",
        **OTEL_BASE,
    )
    rejected(
        "telemetry requires private endpoint",
        otel_sdk_disabled=False,
        otel_private_endpoint="http://collector:4318",
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:4318",
        "https://127.0.0.1",
        "http://10.0.0.5:4318/",
        "http://192.168.1.2:4318",
        "http://[::1]:4318",
        "http://[::ffff:127.0.0.1]:4318",
        "http://[::ffff:10.0.0.1]:4318",
        "http://collector:4318",
        "http://otel-collector.internal:4318",
        "http://a1:4318",
        "http://" + ".".join(["a"] * 2) + ".internal",
    ],
)
def test_private_telemetry_origins_are_accepted(endpoint):
    assert build(**OTEL_BASE, otel_private_endpoint=endpoint).otel_private_endpoint == endpoint


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://169.254.1.1:4318",
        "http://0.0.0.0:4318",
        "http://224.0.0.1:4318",
        "http://8.8.8.8:4318",
        "http://[2606:4700::1]:4318",
        "http://example.com:4318",
        "http://collector.local:4318",
        "http://a_b:4318",
        "http://1abc:4318",
        "http://-abc:4318",
        "http://abc-:4318",
        "http://" + "a" * 64 + ":4318",
        "http://" + ".".join(["a" * 60] * 5) + ".internal",
        "http://:4318",
        "ftp://collector:4318",
        "http://user@collector:4318",
        "http://user:pass@collector:4318",
        "http://collector:4318?x=1",
        "http://collector:4318#frag",
        "http://collector:4318/v1/traces",
        "collector:4318",
    ],
)
def test_non_private_or_decorated_telemetry_origins_are_rejected(endpoint):
    rejected(
        "telemetry endpoint must be a private origin without credentials",
        **OTEL_BASE,
        otel_private_endpoint=endpoint,
    )


@pytest.mark.parametrize("endpoint", ["http://collector:0", "http://collector:99999"])
def test_invalid_telemetry_ports_are_rejected(endpoint):
    rejected("invalid_telemetry_port", **OTEL_BASE, otel_private_endpoint=endpoint)


def test_telemetry_checks_are_skipped_when_sdk_is_disabled():
    config = build(otel_private_endpoint="http://example.com:4318")
    assert config.otel_sdk_disabled


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (
            {
                **OPENAI,
                **PRICING,
                "embeddings_provider": "openai",
                "require_fresh_knowledge": False,
            },
            "production OpenAI requires semantic embeddings and fresh knowledge",
        ),
        (
            {**OPENAI, **PRICING, "require_fresh_knowledge": True},
            "production OpenAI requires semantic embeddings and fresh knowledge",
        ),
        ({"secure_cookies": False}, "production requires HTTPS origins and secure cookies"),
        ({"allowed_origins": ""}, "production requires HTTPS origins and secure cookies"),
        (
            {"allowed_origins": "http://example.org"},
            "production requires HTTPS origins and secure cookies",
        ),
        (
            {"allowed_origins": "https://example.org,https://localhost"},
            "production requires HTTPS origins and secure cookies",
        ),
        (
            {"allowed_origins": "https://127.0.0.1"},
            "production requires HTTPS origins and secure cookies",
        ),
        (
            {"allowed_origins": "https://u@example.org"},
            "production requires HTTPS origins and secure cookies",
        ),
        (
            {"allowed_origins": "https://u:p@example.org"},
            "production requires HTTPS origins and secure cookies",
        ),
        (
            {"allowed_origins": "https://example.org/path"},
            "production requires HTTPS origins and secure cookies",
        ),
        (
            {"allowed_origins": "https://example.org?q=1"},
            "production requires HTTPS origins and secure cookies",
        ),
        (
            {"allowed_origins": "https://example.org#f"},
            "production requires HTTPS origins and secure cookies",
        ),
        (
            {"allowed_origins": "https://"},
            "production requires HTTPS origins and secure cookies",
        ),
        (
            {"database_url": "postgresql://db.internal/app"},
            "production database credentials and host must be explicit",
        ),
        (
            {"database_url": "postgresql://assistant:secret@db.internal/app"},
            "production database credentials and host must be explicit",
        ),
        (
            {"database_url": "postgresql://postgres:secret@db.internal/app"},
            "production database credentials and host must be explicit",
        ),
        (
            {"database_url": "postgresql://app@db.internal/app"},
            "production database credentials and host must be explicit",
        ),
        (
            {"database_url": "postgresql://app:assistant@db.internal/app"},
            "production database credentials and host must be explicit",
        ),
        (
            {"database_url": "postgresql://app:secret@localhost/app"},
            "production database credentials and host must be explicit",
        ),
        (
            {"database_url": "postgresql://app:secret@127.0.0.1/app"},
            "production database credentials and host must be explicit",
        ),
        (
            {"database_url": "postgresql://app:secret@/app"},
            "production database credentials and host must be explicit",
        ),
        (
            {"neo4j_password": "change-me"},
            "production graph credentials and host must be explicit",
        ),
        (
            {"neo4j_uri": "bolt://127.0.0.1:7688"},
            "production graph credentials and host must be explicit",
        ),
        (
            {"neo4j_uri": "bolt://localhost:7687"},
            "production graph credentials and host must be explicit",
        ),
        (
            {"rate_hash_key": "local-fixture-only"},
            "production rate hash key must be random and at least 32 characters",
        ),
        (
            {"rate_hash_key": "short"},
            "production rate hash key must be random and at least 32 characters",
        ),
    ],
)
def test_production_validations_report_exact_messages(values, message):
    rejected(message, **{**PROD_BASE, **values})


def test_production_paid_pricing_must_be_explicit():
    message = "production paid pricing and reservation must be explicitly configured"
    paid = {**PROD_BASE, **OPENAI, "embeddings_provider": "openai", "require_fresh_knowledge": True}
    rejected(message, **paid)
    for missing in PRICING:
        partial = {key: value for key, value in PRICING.items() if key != missing}
        rejected(message, **paid, **partial)
    assert build(**paid, **PRICING).allow_paid_ai


def test_production_checks_run_in_declared_order():
    rejected(
        "production requires HTTPS origins",
        **{**PROD_BASE, "secure_cookies": False, "neo4j_password": "change-me"},
    )
    rejected(
        "production database credentials",
        **{**PROD_BASE, "neo4j_password": "change-me", "database_url": "postgresql://x@h/d"},
    )
    rejected(
        "production graph credentials",
        **{**PROD_BASE, "neo4j_password": "change-me", "rate_hash_key": "short"},
    )
    rejected(
        "production OpenAI requires",
        **{**PROD_OPENAI, "secure_cookies": False, "require_fresh_knowledge": False},
    )


def test_country_proxy_address_count_is_capped_at_sixteen():
    sixteen = ",".join(f"10.0.0.{index}" for index in range(16))
    assert len(build(product_analytics_country_proxy_ips=sixteen).origins) == 2
    rejected(
        "too many country proxy IP addresses",
        product_analytics_country_proxy_ips=sixteen + ",10.0.0.16",
    )
