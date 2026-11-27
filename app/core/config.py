from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FixIt API"
    app_version: str = "0.3.0"
    app_env: str = "development"
    debug: bool = False
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fixit"
    session_cookie_name: str = "fixit_session"
    csrf_cookie_name: str = "fixit_csrf"
    session_ttl_hours: int = 168
    cookie_secure: bool = False
    public_api_url: str = "http://localhost:8000"
    allowed_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:5175"
    )
    mailgun_api_key: str | None = None
    mailgun_domain: str | None = None
    mailgun_from: str = "FixIt <no-reply@localhost>"
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
