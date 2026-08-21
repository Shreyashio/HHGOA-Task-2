"""
backend/config.py
─────────────────
Centralised settings loaded from .env via Pydantic BaseSettings.
All modules import `settings` from here — no os.getenv() sprinkled around.
"""

import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Robustly find project root directory and .env file
_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_DEFAULT_ENV_FILE = _BACKEND_DIR / ".env"
if not _DEFAULT_ENV_FILE.exists():
    _DEFAULT_ENV_FILE = _PROJECT_ROOT / ".env"
if not _DEFAULT_ENV_FILE.exists():
    _DEFAULT_ENV_FILE = Path(".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # STT
    SARVAM_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # LLM
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama-3.1-8b-instant"

    # Vector DB
    CHROMA_PERSIST_DIR: str = str(_PROJECT_ROOT / "chroma_db")
    CHROMA_COLLECTION_NAME: str = "msmarco_xi"

    # Embedding
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Retrieval
    TOP_K_RETRIEVE: int = 10
    TOP_K_FINAL: int = 3

    # Chunking
    CHUNKING_STRATEGY: str = "sentence"
    CHUNK_SIZE: int = 256
    CHUNK_OVERLAP: int = 32

    # App
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"
    LOG_LEVEL: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
