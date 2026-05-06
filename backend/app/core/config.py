from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
    env_file=str(ROOT_DIR / ".env"),
    env_file_encoding="utf-8",
    extra="ignore"
)
    DATABASE_URL: Optional[str] = None
    POSTGRES_URL: str
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: str = "postgres"
    SECRET_KEY: str = "dev-secret-key-change-me"
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = ""

    @property
    def resolved_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.POSTGRES_URL:
            return self.POSTGRES_URL
        raise ValueError("DATABASE_URL is not configured")

settings = Settings()