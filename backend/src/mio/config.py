from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_prefix="MIO_",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://mio:mio@localhost:5432/mio"
    llm_provider: Literal["mock", "openai_compatible"] = "mock"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "mock-mio"
    mock_chunk_delay_ms: int = Field(default=0, ge=0)
    cors_origins: list[str] = ["http://localhost:5173"]
    context_message_limit: int = Field(default=20, ge=1, le=100)


@lru_cache
def get_settings() -> Settings:
    return Settings()
