"""
backend/config.py
─────────────────
Centralised settings loaded from .env via Pydantic BaseSettings.
All modules import `settings` from here — no os.getenv() sprinkled around.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # STT
    SARVAM_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # LLM
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama-3.1-8b-instant"

    # Vector DB
    CHROMA_PERSIST_DIR: str = "./chroma_db"
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
    CORS_ORIGINS: str = "http://localhost:5173"
    LOG_LEVEL: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
