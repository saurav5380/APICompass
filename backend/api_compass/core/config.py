from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MailProvider(str, Enum):
    SENDGRID = "sendgrid"
    SES = "ses"


PLACEHOLDER_VALUES = {"", "replace-me", "changeme"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="local", alias="ENVIRONMENT")
    project_name: str = Field(default="API Compass", alias="PROJECT_NAME")
    version: str = Field(default="0.1.0")
    api_prefix: str = Field(default="/api")

    database_url: PostgresDsn = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:15432/api_compass",
        alias="DATABASE_URL",
    )
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    worker_broker_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        alias="WORKER_BROKER_URL",
    )
    worker_result_backend: RedisDsn = Field(
        default="redis://localhost:6379/1",
        alias="WORKER_RESULT_BACKEND",
    )

    secret_key: SecretStr = Field(alias="SECRET_KEY")
    encryption_key: SecretStr = Field(
        alias="ENCRYPTION_KEY",
        description="Base64-encoded AES-256 key used to encrypt provider auth blobs.",
    )

    mail_provider: MailProvider = Field(default=MailProvider.SENDGRID, alias="MAIL_PROVIDER")
    sendgrid_api_key: SecretStr | None = Field(default=None, alias="SENDGRID_API_KEY")
    ses_access_key_id: str | None = Field(default=None, alias="SES_ACCESS_KEY_ID")
    ses_secret_access_key: SecretStr | None = Field(default=None, alias="SES_SECRET_ACCESS_KEY")
    ses_region: str | None = Field(default=None, alias="SES_REGION")

    openai_api_key: SecretStr = Field(alias="OPENAI_API_KEY")
    twilio_account_sid: str = Field(alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: SecretStr = Field(alias="TWILIO_AUTH_TOKEN")
    slack_bot_token: SecretStr = Field(alias="SLACK_BOT_TOKEN")

    stripe_secret_key: SecretStr = Field(alias="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field(alias="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: SecretStr = Field(alias="STRIPE_WEBHOOK_SECRET")

    @staticmethod
    def _is_missing(value: Any) -> bool:
        if value is None:
            return True

        if isinstance(value, SecretStr):
            value = value.get_secret_value()

        if isinstance(value, str):
            return value.strip() in PLACEHOLDER_VALUES

        return False

    @model_validator(mode="after")
    def ensure_required_secrets(self) -> "Settings":
        required: dict[str, Any] = {
            "SECRET_KEY": self.secret_key,
            "ENCRYPTION_KEY": self.encryption_key,
            "SLACK_BOT_TOKEN": self.slack_bot_token,
            "OPENAI_API_KEY": self.openai_api_key,
            "TWILIO_ACCOUNT_SID": self.twilio_account_sid,
            "TWILIO_AUTH_TOKEN": self.twilio_auth_token,
            "STRIPE_SECRET_KEY": self.stripe_secret_key,
            "STRIPE_WEBHOOK_SECRET": self.stripe_webhook_secret,
        }

        if self.mail_provider == MailProvider.SENDGRID:
            required["SENDGRID_API_KEY"] = self.sendgrid_api_key
        elif self.mail_provider == MailProvider.SES:
            required["SES_ACCESS_KEY_ID"] = self.ses_access_key_id
            required["SES_SECRET_ACCESS_KEY"] = self.ses_secret_access_key
            required["SES_REGION"] = self.ses_region

        missing = [name for name, value in required.items() if self._is_missing(value)]

        if missing:
            missing_csv = ", ".join(sorted(missing))
            raise ValueError(
                "Missing required secrets. Set the following environment variables with real values: "
                f"{missing_csv}."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]


settings = get_settings()
