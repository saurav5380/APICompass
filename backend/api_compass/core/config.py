from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="local", alias="ENVIRONMENT")
    project_name: str = Field(default="API Compass")
    version: str = Field(default="0.1.0")
    api_prefix: str = Field(default="/api")

    database_url: PostgresDsn = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/api_compass",
        alias="DATABASE_URL",
    )
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )

    secret_key: str = Field(default="insecure-local-secret", alias="SECRET_KEY")
    encryption_key: str = Field(
        default="insecure-generated-key",
        alias="ENCRYPTION_KEY",
        description=(
            "Base64-encoded AES-256 key used to encrypt provider auth blobs. Replace in prod."
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]


settings = get_settings()
