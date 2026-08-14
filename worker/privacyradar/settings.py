from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT.parent / ".env", ROOT / ".env"),
        extra="ignore",
    )

    database_url: str = "postgresql://privacyradar:privacyradar@localhost:5433/privacyradar"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    openai_extract_model: str = "gpt-4.1-mini"
    openai_hard_model: str = "gpt-5.6"
    crawl_user_agent: str = "privacyradar/0.1 (+https://privacyradar.local; research crawler)"
    crawl_delay_seconds: float = 2.0
    playwright_fallback: bool = False
    firecrawl_api_key: str = ""
    catalog_path: Path = ROOT / "data" / "catalog.yaml"
    auth_secret: str = ""
    notify_signing_key: str = ""
    notify_provider: str = "fake"
    notify_from: str = "PrivacyRadar <alerts@privacyradar.local>"
    public_base_url: str = "http://127.0.0.1:3000"
    resend_api_key: str = ""
    resend_webhook_secret: str = ""


settings = Settings()
