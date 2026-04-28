from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE_DIR = REPO_ROOT / "engine"
SCRIPTS_DIR = ENGINE_DIR / "scripts"
REFERENCES_DIR = ENGINE_DIR / "references"
SKILL_MD = ENGINE_DIR / "SKILL.md"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-7"
    api_host: str = "127.0.0.1"
    api_port: int = 8765
    cors_origin: str = "http://localhost:8501"


settings = Settings()
