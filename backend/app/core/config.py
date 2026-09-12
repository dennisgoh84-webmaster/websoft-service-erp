"""
Application configuration.

Values are read from environment variables (or a local .env file, not
committed to git). Defaults here are for local development only.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Websoft Service ERP Solution"
    environment: str = "development"

    database_url: str = (
        "postgresql+psycopg://websoft_app:websoft_dev_local@localhost:5432/websoft_service_erp"
    )

    # Demo-only secret. Must be overridden via env var before any real deployment.
    jwt_secret_key: str = "dev-only-secret-do-not-use-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8-hour session for demo convenience

    # Outbound email (2026-09-12: "Email PO" -- real server-side send with a
    # PDF attached). One shared mailbox/relay for the whole install, not
    # per-company -- unset by default so "Email" fails with a clear message
    # instead of silently pretending to send. Set these in backend/.env
    # (gitignored) to a real SMTP account before using it.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from_email: str | None = None
    smtp_from_name: str = "Web Master Consultancy"


settings = Settings()
