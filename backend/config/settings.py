from pydantic_settings import BaseSettings
from pydantic import field_validator, computed_field
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "eToro Portfolio Manager"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite+aiosqlite:///./etoro_portfolio.db"
    POSTGRES_URL: str | None = None
    SECRET_KEY: str = "change-me-in-production-use-a-real-secret"
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None
    CLAUDE_API_KEY: str | None = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    ETORO_API_KEY: str | None = None
    ETORO_USERNAME: str | None = None
    ETORO_PUBLIC_API_KEY: str | None = None
    ETORO_USER_KEY: str | None = None
    PAPER_TRADING: bool = True
    MAX_PORTFOLIO_DRAWDOWN: float = 0.25
    MAX_ALLOCATION_PER_TRADER: float = 0.30
    MIN_DIVERSIFICATION: int = 3
    COOLDOWN_DAYS_AFTER_LOSS: int = 7
    VOLATILITY_EXPOSURE_REDUCTION: float = 0.5
    LOG_LEVEL: str = "INFO"
    ENABLE_AUTOMATION: bool = False
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    PORT: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()

SQLALCHEMY_DATABASE_URL = settings.POSTGRES_URL if settings.POSTGRES_URL else settings.DATABASE_URL
