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


settings = Settings()
