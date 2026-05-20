import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHANNEL_ID: str
    API_SECURITY_KEY: str = "rifar_secret_key_2026"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"

    # Thresholds (in meters)
    WARNING_LEVEL: float = 4.0   # ⚠️ Yellow — elevated risk (Warning)
    DANGER_LEVEL: float = 4.5    # 🚨 Red   — flooding imminent (Critical)

    # Anti-spam: minimum minutes between repeated alerts at the same level
    COOLDOWN_MINUTES: int = 30

    @property
    def cors_origins(self) -> List[str]:
        return [item.strip() for item in self.CORS_ALLOWED_ORIGINS.split(",") if item.strip()]

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
