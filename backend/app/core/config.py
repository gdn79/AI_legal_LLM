from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Local Legal LLM Backend"
    app_env: str = "local"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./legal_ai.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    storage_path: Path = Path("./storage")
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "legal_rag"
    llm_base_url: str = "http://localhost:8010"
    llm_api_key: str = "stub-key"
    llm_model: str = "stub-openai-compatible"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 512
    embedding_model: str = "stub-embedding"
    rag_top_k: int = 5
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 150
    fns_provider_mode: str = "MOCK_FOR_DEV"
    fns_provider: str = "mock_fns_adapter"
    fns_api_base_url: str = "https://dev-null.local/fns"
    fns_sandbox_base_url: str = "https://sandbox.dev-null.local/fns"
    fns_sandbox_token: str = ""
    fns_sandbox_client_id: str = ""
    fns_sandbox_client_secret: str = ""
    fns_timeout_seconds: int = 30
    fns_max_retries: int = 2
    fns_retry_backoff_seconds: int = 2
    fns_rate_limit_per_minute: int = 30
    enable_fns_sandbox: bool = False
    russian_post_mode: str = "MOCK_FOR_DEV"
    russian_post_provider: str = "mock_russian_post_adapter"
    court_provider_mode: str = "MOCK_FOR_DEV"
    russian_post_api_base_url: str = "https://dev-null.local/russian-post"
    russian_post_sandbox_base_url: str = "https://sandbox.dev-null.local/russian-post"
    russian_post_timeout_seconds: int = 30
    russian_post_max_retries: int = 1
    russian_post_retry_backoff_seconds: int = 1
    russian_post_rate_limit_per_minute: int = 10
    russian_post_app_token: str = ""
    russian_post_user_key: str = ""
    russian_post_sandbox_app_token: str = ""
    russian_post_sandbox_user_key: str = ""
    russian_post_sandbox_client_secret: str = ""
    enable_russian_post_sandbox: bool = False
    enable_real_post_send: bool = False
    enable_real_fns: bool = False
    court_arbitr_base_url: str = "https://dev-null.local/court-arbitr"
    court_sandbox_base_url: str = "https://sandbox.dev-null.local/court-arbitr"
    court_arbitr_provider: str = "mock_court_arbitr_adapter"
    court_arbitr_timeout_seconds: int = 30
    court_arbitr_max_retries: int = 1
    court_arbitr_retry_backoff_seconds: int = 2
    court_arbitr_rate_limit_per_minute: int = 10
    court_sandbox_token: str = ""
    court_provider_sandbox_api_key: str = ""
    court_sandbox_client_secret: str = ""
    enable_court_sandbox: bool = False
    enable_real_court_search: bool = False
    enable_court_submission: bool = False
    enable_public_kad_search: bool = False
    seed_on_startup: bool = True
    seed_password: str = "ChangeMe123!"
    admin_email: str = "admin@example.com"
    lawyer_email: str = "lawyer@example.com"
    manager_email: str = "manager@example.com"
    initiator_email: str = "initiator@example.com"
    service_agent_email: str = "service-agent@example.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("fns_provider_mode")
    @classmethod
    def validate_fns_provider_mode(cls, value: str) -> str:
        allowed = {
            "MOCK_FOR_DEV",
            "MANUAL_UPLOAD",
            "LOCAL_EGRUL_FILES",
            "FNS_SANDBOX_DISABLED",
            "FNS_SANDBOX_READY",
            "FNS_PRODUCTION_DISABLED",
            "OFFICIAL_FNS_INTEGRATION_DISABLED",
        }
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError(f"Unsupported FNS provider mode: {value}")
        return normalized

    @field_validator("russian_post_mode")
    @classmethod
    def validate_russian_post_mode(cls, value: str) -> str:
        allowed = {
            "MOCK_FOR_DEV",
            "MANUAL_UPLOAD",
            "RUSSIAN_POST_SANDBOX_DISABLED",
            "RUSSIAN_POST_SANDBOX_READY",
            "RUSSIAN_POST_PRODUCTION_DISABLED",
            "RUSSIAN_POST_OTPRAVKA_API_DISABLED",
            "RUSSIAN_POST_EZP_API_DISABLED",
        }
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError(f"Unsupported Russian Post mode: {value}")
        return normalized

    @field_validator("court_provider_mode")
    @classmethod
    def validate_court_provider_mode(cls, value: str) -> str:
        allowed = {
            "MOCK_FOR_DEV",
            "MANUAL_IMPORT",
            "COURT_SANDBOX_DISABLED",
            "COURT_SANDBOX_READY",
            "PRODUCTION_DISABLED",
            "PUBLIC_SEARCH_DISABLED",
            "OFFICIAL_API_DISABLED",
            "LICENSED_PROVIDER_API_DISABLED",
            "LICENSED_PROVIDER_SANDBOX_DISABLED",
        }
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError(f"Unsupported court provider mode: {value}")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
