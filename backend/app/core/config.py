from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "KeyVerhaus"
    environment: Literal["dev", "test", "prod"] = "dev"

    database_url: str = "postgresql+asyncpg://localhost:5432/key_warehouse"

    # Auth
    jwt_secret: str = "dev-secret-change-me-in-production-please-32b"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    email_verify_ttl_hours: int = 48
    password_reset_ttl_minutes: int = 60
    invitation_ttl_days: int = 7
    terms_version: str = "2026-11"

    # Brute-force / flood protection. trust_proxy_headers=true only behind your own
    # reverse proxy (nginx, Caddy), otherwise clients could fake their IP.
    rate_limit_enabled: bool = True
    trust_proxy_headers: bool = False

    # Uploaded files (item photos). Local folder now, object storage (S3) later.
    media_dir: str = "media"

    # Links in e-mails point to the frontend
    frontend_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173"]

    # E-mail: console (prints to log), memory (tests), smtp (Brevo / Mailpit / any SMTP)
    email_backend: Literal["console", "memory", "smtp"] = "console"
    email_from: str = "KeyVerhaus <no-reply@keyverhaus.com>"
    smtp_host: str = "smtp-relay.brevo.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True


settings = Settings()
