from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/filmdb"

    # ── JWT ───────────────────────────────────────────────────────────────
    # Generate a strong key with: openssl rand -hex 32
    SECRET_KEY: str = "insecure-dev-key-replace-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Application ───────────────────────────────────────────────────────
    APP_NAME: str = "Film Recommendation API"
    DEBUG: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once at startup)."""
    return Settings()
