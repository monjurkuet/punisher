from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Punisher"
    DEBUG: bool = False
    DATA_DIR: Path = Path("data")

    # LLM
    LLM_API_BASE: str = "http://localhost:8087/v1"
    OLLAMA_API_BASE: str = "http://localhost:11434/v1"
    LLM_MODEL: str = "gemini-2.5-flash-lite"

    # Search
    SEARCH_ENGINE_URL: str = "http://localhost:9345"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""

    # Crypto
    HYPERLIQUID_WALLET_ADDRESS: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
