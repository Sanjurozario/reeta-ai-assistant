import os
import sys
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_reeta_base_dir() -> Path:
    """Returns persistent application directory in %LOCALAPPDATA%\\REETA or ~/.reeta."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        p = Path(local_app_data) / "REETA"
    else:
        p = Path.home() / ".reeta"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_reeta_data_dir() -> Path:
    """Directory for SQLite database, models, and cognitive embeddings cache."""
    p = get_reeta_base_dir() / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_reeta_logs_dir() -> Path:
    """Directory for rotating desktop and backend application logs."""
    p = get_reeta_base_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_stored_credential(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieves an API key from Windows Credential Manager or environment variables."""
    val = os.environ.get(key)
    if val:
        return val
    try:
        import keyring
        val = keyring.get_password("REETA", key)
        if val:
            return val
    except Exception:
        pass
    return default


def set_stored_credential(key: str, value: str) -> bool:
    """Saves an API key securely to Windows Credential Manager (WinVault)."""
    try:
        import keyring
        keyring.set_password("REETA", key, value)
        return True
    except Exception:
        return False


def is_postgres_available(host: str = "127.0.0.1", port: int = 5433) -> bool:
    """Probes PostgreSQL port with a fast 150ms socket check."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=0.15):
            return True
    except OSError:
        return False


class Settings(BaseSettings):
    """REETA Global Configuration Schema backed by Pydantic Settings, keyring and .env."""

    # Server Configuration & Security
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "reeta_development_secret_key_super_secure_32_bytes_2026_x9"
    REETA_STANDALONE: bool = False
    REETA_LAUNCH_TOKEN: Optional[str] = None

    # Dual Database: PostgreSQL (dev/tests/docker) & SQLite + sqlite-vec (desktop standalone)
    DATABASE_URL: str = "postgresql+asyncpg://reeta_admin:reeta_secure_password_2026@127.0.0.1:5433/reeta_db"
    POSTGRES_USER: str = "reeta_admin"
    POSTGRES_PASSWORD: str = "reeta_secure_password_2026"
    POSTGRES_DB: str = "reeta_db"
    POSTGRES_PORT: int = 5433

    # AI Model Gateway & Reasoning Providers
    # Primary: Cloud models (Gemini / OpenAI / Anthropic); Optional: Local Ollama
    DEFAULT_MODEL_PROVIDER: str = "gemini"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3.1:latest"

    # Cloud LLM API Keys (Windows Credential Manager / Env)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_DEFAULT_MODEL: str = "gpt-4o"

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_DEFAULT_MODEL: str = "claude-3-5-sonnet-20241022"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_DEFAULT_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.8-flash"
    GEMINI_BASE_URL: Optional[str] = "https://generativelanguage.googleapis.com/v1beta/openai/"

    GROQ_API_KEY: Optional[str] = None

    # Vector Embeddings
    EMBEDDING_PROVIDER: str = "local"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Voice & Speech Pipeline
    VOICE_ENABLED: bool = True
    STT_MODEL_SIZE: str = "base.en"
    TTS_ENGINE: str = "sapi"  # "sapi" (offline Windows SAPI), "edge-tts", or "openai"
    EDGE_TTS_VOICE: str = "en-US-AriaNeural"
    WAKE_WORD: str = "Hey Reeta"
    VAD_THRESHOLD: float = 0.5

    # Automation & Sandboxing
    AUTHORIZED_WORKSPACE: str = str(Path(__file__).resolve().parent.parent.parent)
    DOCKER_SANDBOX_ENABLED: bool = True
    PLAYWRIGHT_HEADLESS: bool = True
    BROWSER_CHANNEL: str = "msedge"
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

    def is_standalone(self) -> bool:
        """Determines if the backend is running in standalone desktop mode."""
        return (
            self.REETA_STANDALONE
            or getattr(sys, "frozen", False)
            or os.environ.get("REETA_STANDALONE", "").lower() in ("1", "true", "yes")
        )

    def get_database_url(self) -> str:
        """Dynamically resolves DATABASE_URL for SQLite or PostgreSQL."""
        if (
            self.is_standalone()
            or os.environ.get("USE_SQLITE", "").lower() in ("1", "true", "yes")
            or not is_postgres_available("127.0.0.1", self.POSTGRES_PORT)
        ):
            db_path = get_reeta_data_dir() / "reeta.db"
            return f"sqlite+aiosqlite:///{db_path}"
        return self.DATABASE_URL


settings = Settings()

# Normalize provider name to lowercase
settings.DEFAULT_MODEL_PROVIDER = (settings.DEFAULT_MODEL_PROVIDER or "gemini").lower().strip()

# Resolve API keys from Windows Credential Manager if missing from .env
if not settings.GEMINI_API_KEY:
    settings.GEMINI_API_KEY = get_stored_credential("GEMINI_API_KEY")
if not settings.OPENAI_API_KEY:
    settings.OPENAI_API_KEY = get_stored_credential("OPENAI_API_KEY")

# Auto-resolve DATABASE_URL (falls back to local SQLite if Postgres is not reachable)
settings.DATABASE_URL = settings.get_database_url()
