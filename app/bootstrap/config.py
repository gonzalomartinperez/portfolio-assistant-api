from decimal import Decimal
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.budget import Budget


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.local', extra='ignore')
    environment: Literal['development', 'production'] = 'development'
    database_url: str = 'postgresql://assistant:assistant@127.0.0.1:5433/assistant'
    neo4j_uri: str = 'bolt://127.0.0.1:7688'
    neo4j_user: str = 'neo4j'
    neo4j_password: str = 'change-me'
    allowed_origins: str = 'http://localhost:3000,http://localhost:3001'
    ai_provider: str = 'fixture'
    embeddings_provider: str = 'fixture'
    allow_paid_ai: bool = False
    openai_api_key: str | None = None
    openai_model: str = 'gpt-6-luna'
    secure_cookies: bool = False
    retention_days: int = Field(default=7, ge=1, le=30)
    run_timeout_seconds: float = Field(default=60, gt=0, le=120)
    rate_hash_key: str = 'local-fixture-only'
    trusted_proxy_ips: str = ''
    monthly_budget_usd: str = '10.00'
    reserve_cutoff_usd: str = '9.00'
    reservation_usd: str = '0.05'
    input_usd_per_million: str = '0.10'
    output_usd_per_million: str = '0.50'

    @model_validator(mode='after')
    def safe_configuration(self):
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
        if self.embeddings_provider != 'fixture':
            raise ValueError('only fixture embeddings are implemented')
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
