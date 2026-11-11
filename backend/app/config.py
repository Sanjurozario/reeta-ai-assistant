import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """REETA Global Configuration Schema backed by Pydantic Settings and .env."""

    # Server Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "reeta_development_secret_key_super_secure_32_bytes_2026_x9"

    # PostgreSQL Database
    DATABASE_URL: str = "postgresql+asyncpg://reeta_admin:reeta_secure_password_2026@127.0.0.1:5433/reeta_db"
    POSTGRES_USER: str = "reeta_admin"
    POSTGRES_PASSWORD: str = "reeta_secure_password_2026"
    POSTGRES_DB: str = "reeta_db"
    POSTGRES_PORT: int = 5433

    # AI Model Gateway & Reasoning Providers
    # Primary: Cloud models (OpenAI / Anthropic / Gemini); Optional: Local Ollama
    DEFAULT_MODEL_PROVIDER: str = "openai"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.1:latest"

    # Cloud LLM API Keys (Optional; backend boots without them)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_DEFAULT_MODEL: str = "gpt-4o"

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_DEFAULT_MODEL: str = "claude-3-5-sonnet-20241022"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_DEFAULT_MODEL: str = "gemini-1.5-pro"

    GROQ_API_KEY: Optional[str] = None

    # Vector Embeddings
    EMBEDDING_PROVIDER: str = "local"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Voice & Speech Pipeline
    VOICE_ENABLED: bool = False
    STT_MODEL_SIZE: str = "base.en"
    TTS_ENGINE: str = "edge-tts"
    EDGE_TTS_VOICE: str = "en-US-AriaNeural"
    WAKE_WORD: str = "Hey Reeta"
    VAD_THRESHOLD: float = 0.5

    # Automation & Sandboxing
    AUTHORIZED_WORKSPACE: str = str(Path(__file__).resolve().parent.parent.parent)
    DOCKER_SANDBOX_ENABLED: bool = True
    PLAYWRIGHT_HEADLESS: bool = True
    UI_AUTOMATION_TIMEOUT_MS: int = 15000

    # Security & Zero-Trust Approvals
    APPROVAL_TICKET_TTL_SECONDS: int = 300
    REQUIRE_APPROVAL_FOR_HOST_TERMINAL: bool = True
    REQUIRE_APPROVAL_FOR_FILE_DELETION: bool = True
    REQUIRE_APPROVAL_FOR_EXTERNAL_NETWORK: bool = True

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
