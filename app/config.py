from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.local', extra='ignore')
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
    retention_days: int = 7
    rate_hash_key: str = 'local-fixture-only'
    monthly_budget_usd: str = '10.00'
    reserve_cutoff_usd: str = '9.00'
    reservation_usd: str = '0.05'
    input_usd_per_million: str = '0.10'
    output_usd_per_million: str = '0.50'

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(',') if origin.strip()]

    @property
    def cookie_name(self) -> str:
        return '__Host-assistant_session' if self.secure_cookies else 'assistant_session_dev'


@lru_cache
def settings() -> Settings:
    return Settings()
