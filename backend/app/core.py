from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Poopr API"
    database_url: str = "sqlite:///./poopr.db"
    cors_origins: str = Field(default="http://localhost:5173")
    auth_mode: str = "dev"
    app_base_url: str = "http://localhost:5173"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_path: str = "/.auth/login/google/callback"
    session_secret: str = "dev-session-secret-change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

