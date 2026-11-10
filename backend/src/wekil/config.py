from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore")

    database_url: str = "sqlite:///./wekil.db"
    app_secret: str = "dev-secret-change-me"
    frontend_url: str = "http://localhost:5173"
    cron_secret: str = "dev-cron"

    analyst_email: str = "analyst@wekil.local"
    analyst_password: str = "wekil-demo"

    gemini_api_key: str = ""
    gemini_models: str = "gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    agent_email: str = "abenezeralebachew3@gmail.com"
    timezone: str = "Africa/Addis_Ababa"

    companies_house_key: str = ""

    @property
    def models(self) -> list[str]:
        return [m.strip() for m in self.gemini_models.split(",") if m.strip()]


@lru_cache
def settings() -> Settings:
    return Settings()
