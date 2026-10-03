from decimal import Decimal
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.budget import Budget


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env.local', extra='ignore', hide_input_in_errors=True
    )
    environment: Literal['development', 'production'] = 'development'
    database_url: str = Field(
        default='postgresql://assistant:assistant@127.0.0.1:5433/assistant', repr=False
    )
    neo4j_uri: str = 'bolt://127.0.0.1:7688'
    neo4j_user: str = 'neo4j'
    neo4j_password: str = Field(default='change-me', repr=False)
    allowed_origins: str = 'http://localhost:3000,http://localhost:3001'
    ai_provider: Literal['fixture', 'openai'] = 'fixture'
    embeddings_provider: Literal['fixture', 'openai'] = 'fixture'
    allow_paid_ai: bool = False
    openai_api_key: str | None = Field(default=None, repr=False)
    openai_model: Literal['gpt-6-luna'] = 'gpt-6-luna'
    openai_reasoning_effort: Literal['medium'] = 'medium'
    neo4j_database: str = 'neo4j'
    knowledge_poll_seconds: int = Field(default=60, ge=10, le=300)
    knowledge_freshness_seconds: int = Field(default=90, ge=30, le=600)
    require_fresh_knowledge: bool = False
    langsmith_tracing: bool = False
    langchain_tracing_v2: bool = False
    langchain_tracing: bool = False
    langsmith_tracing_v2: bool = False
    openai_log: Literal['', 'error'] = ''
    otel_sdk_disabled: bool = True
    secure_cookies: bool = False
    retention_days: int = Field(default=7, ge=1, le=30)
    run_timeout_seconds: float = Field(default=60, gt=0, le=120)
    rate_hash_key: str = Field(default='local-fixture-only', repr=False)
    trusted_proxy_ips: str = ''
    monthly_budget_usd: str = Field(default='10.00', pattern=r'^\d+(?:\.\d+)?$')
    reserve_cutoff_usd: str = Field(default='10.00', pattern=r'^\d+(?:\.\d+)?$')
    reservation_usd: str = Field(default='0.05', pattern=r'^\d+(?:\.\d+)?$')
    input_usd_per_million: str = Field(default='0.10', pattern=r'^\d+(?:\.\d+)?$')
    output_usd_per_million: str = Field(default='0.50', pattern=r'^\d+(?:\.\d+)?$')
    embedding_usd_per_million: str = Field(default='0.02', pattern=r'^\d+(?:\.\d+)?$')

    @model_validator(mode='after')
    def safe_configuration(self):
        if (
            self.langsmith_tracing
            or self.langchain_tracing_v2
            or self.langchain_tracing
            or self.langsmith_tracing_v2
            or not self.otel_sdk_disabled
        ):
            raise ValueError('external tracing is disabled for this application')
        if Decimal(self.monthly_budget_usd) > 10:
            raise ValueError('monthly budget must not exceed the approved USD 10')
        Budget(
            *(
                Decimal(value)
                for value in (
                    self.monthly_budget_usd,
                    self.reserve_cutoff_usd,
                    self.reservation_usd,
                    self.input_usd_per_million,
                    self.output_usd_per_million,
                )
            )
        )
        if (
            not Decimal(self.embedding_usd_per_million).is_finite()
            or Decimal(self.embedding_usd_per_million) <= 0
        ):
            raise ValueError('embedding price must be finite and positive')
        if self.embeddings_provider == 'openai' and (
            self.ai_provider != 'openai'
            or not self.allow_paid_ai
            or not self.openai_api_key
        ):
            raise ValueError('OpenAI embeddings require explicit paid authorization')
        if self.knowledge_freshness_seconds <= self.knowledge_poll_seconds:
            raise ValueError('freshness interval must exceed polling interval')
        if self.ai_provider != 'fixture' and (
            self.ai_provider != 'openai'
            or not self.allow_paid_ai
            or not self.openai_api_key
        ):
            raise ValueError(
                'paid provider requires explicit provider, allowance and key'
            )
        if self.allow_paid_ai and self.ai_provider != 'openai':
            raise ValueError('paid allowance requires the OpenAI provider')
        if self.environment == 'production':
            if self.ai_provider == 'openai' and (
                not self.require_fresh_knowledge or self.embeddings_provider != 'openai'
            ):
                raise ValueError(
                    'production OpenAI requires semantic embeddings and fresh knowledge'
                )
            db = urlparse(self.database_url)
            parsed_origins = [urlparse(origin) for origin in self.origins]
            if (
                not self.secure_cookies
                or not parsed_origins
                or any(
                    origin.scheme != 'https'
                    or not origin.hostname
                    or origin.username
                    or origin.password
                    or origin.path
                    or origin.params
                    or origin.query
                    or origin.fragment
                    or origin.hostname in ('localhost', '127.0.0.1')
                    for origin in parsed_origins
                )
            ):
                raise ValueError('production requires HTTPS origins and secure cookies')
            if (
                db.username in (None, 'assistant', 'postgres')
                or db.password in (None, 'assistant')
                or db.hostname in (None, 'localhost', '127.0.0.1')
            ):
                raise ValueError(
                    'production database credentials and host must be explicit'
                )
            if self.neo4j_password == 'change-me' or self.neo4j_uri in (
                'bolt://127.0.0.1:7688',
                'bolt://localhost:7687',
            ):
                raise ValueError(
                    'production graph credentials and host must be explicit'
                )
            if (
                self.rate_hash_key == 'local-fixture-only'
                or len(self.rate_hash_key) < 32
            ):
                raise ValueError(
                    'production rate hash key must be random and at least 32 characters'
                )
            if (
                self.allow_paid_ai
                and not {
                    'input_usd_per_million',
                    'output_usd_per_million',
                    'reservation_usd',
                }
                <= self.model_fields_set
            ):
                raise ValueError(
                    'production paid pricing and reservation must be explicitly configured'
                )
        return self

    @property
    def origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(',')
            if origin.strip()
        ]

    @property
    def cookie_name(self) -> str:
        return (
            '__Host-assistant_session'
            if self.secure_cookies
            else 'assistant_session_dev'
        )


@lru_cache
def settings() -> Settings:
    return Settings()
