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
        env_file=(".env", ".env.local", ".env.example"),
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
    worker_poll_interval_seconds: int = Field(
        default=3600,
        alias="WORKER_POLL_INTERVAL_SECONDS",
        ge=300,
        le=21600,
    )
    worker_poll_jitter_ratio: float = Field(
        default=0.1,
        alias="WORKER_POLL_JITTER_RATIO",
        ge=0.0,
        le=0.5,
    )
    worker_retry_max_attempts: int = Field(
        default=5,
        alias="WORKER_RETRY_MAX_ATTEMPTS",
        ge=1,
        le=10,
    )
    worker_retry_backoff_seconds: int = Field(
        default=30,
        alias="WORKER_RETRY_BACKOFF_SECONDS",
        ge=5,
        le=600,
    )
    worker_idempotency_ttl_seconds: int = Field(
        default=5400,
        alias="WORKER_IDEMPOTENCY_TTL_SECONDS",
        ge=60,
        le=14400,
    )
    alerts_default_recipient: str | None = Field(
        default=None,
        alias="ALERTS_DEFAULT_RECIPIENT",
        description="Fallback email address for alert notifications and digests.",
    )
    alerts_email_sender: str = Field(
        default="alerts@api-compass.local",
        alias="ALERTS_EMAIL_SENDER",
    )
    alerts_quiet_hours_start: str = Field(
        default="22:00",
        alias="ALERTS_QUIET_HOURS_START",
        description="UTC time (HH:MM) when alerts pause.",
    )
    alerts_quiet_hours_end: str = Field(
        default="06:00",
        alias="ALERTS_QUIET_HOURS_END",
        description="UTC time (HH:MM) when alerts resume.",
    )
    alerts_spike_multiplier: float = Field(
        default=1.5,
        alias="ALERTS_SPIKE_MULTIPLIER",
        ge=1.1,
        le=5.0,
    )
    alerts_spike_minimum: float = Field(
        default=100.0,
        alias="ALERTS_SPIKE_MINIMUM",
        ge=0.0,
    )
    alerts_digest_hour_utc: int = Field(
        default=12,
        alias="ALERTS_DIGEST_HOUR_UTC",
        ge=0,
        le=23,
    )
    alerts_debounce_minutes: int = Field(
        default=60,
        alias="ALERTS_DEBOUNCE_MINUTES",
        ge=5,
        le=360,
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    raw_event_retention_days: int = Field(
        default=180,
        alias="RAW_EVENT_RETENTION_DAYS",
        ge=30,
        le=365,
        description="How long to retain raw usage events before purging.",
    )
    usage_backfill_days: int = Field(
        default=45,
        alias="USAGE_BACKFILL_DAYS",
        ge=1,
        le=120,
    )
    usage_backfill_timeout_seconds: int = Field(
        default=300,
        alias="USAGE_BACKFILL_TIMEOUT_SECONDS",
        ge=30,
        le=1800,
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
    sentry_dsn: SecretStr | None = Field(default=None, alias="SENTRY_DSN")

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
