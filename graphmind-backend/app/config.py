from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "GraphMind"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = Field(..., validation_alias="REDIS_URL")

    # Supabase
    supabase_url: str = Field(..., validation_alias="SUPABASE_URL")
    supabase_anon_key: str = Field(..., validation_alias="SUPABASE_ANON_KEY")
    supabase_service_key: str = Field(..., validation_alias="SUPABASE_SERVICE_KEY")
    supabase_storage_bucket: str = "graphmind-repos"

    # GitHub OAuth
    github_client_id: str = Field(..., validation_alias="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(..., validation_alias="GITHUB_CLIENT_SECRET")
    github_redirect_uri: str = Field(..., validation_alias="GITHUB_REDIRECT_URI")

    # JWT
    secret_key: str = Field(..., validation_alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Anthropic
    anthropic_api_key: str = Field(..., validation_alias="ANTHROPIC_API_KEY")
    anthropic_model: str = "claude-sonnet-4-6"

    # Qdrant
    qdrant_url: str = Field(..., validation_alias="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(None, validation_alias="QDRANT_API_KEY")

    # Celery
    celery_broker_url: str = Field(..., validation_alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(..., validation_alias="CELERY_RESULT_BACKEND")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        validation_alias="CORS_ORIGINS",
    )

    # Rate limiting
    rate_limit_imports_per_day: int = 10
    rate_limit_chat_per_day: int = 100

    # File upload
    max_upload_size_mb: int = 100

    # Embedding model
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache
def get_settings() -> Settings:
    return Settings()