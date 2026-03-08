from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # --- ОСНОВНЫЕ НАСТРОЙКИ ---
    BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    
    # --- CLOUDFLARE R2 ---
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_NAME: str
    S3_PUBLIC_URL: str

    # --- API KEYS ---
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet" # Наш новый "мозг"
    OPENAI_API_KEY: str
    CREATOMATE_API_KEY: str
    CREATOMATE_TEMPLATE_ID: str
    
    # --- VIZARD (OFF BY DEFAULT) ---
    VIZARD_API_KEY: Optional[str] = None
    ENABLE_VIZARD: bool = False # Флаг включения Vizard

    # --- МОНИТОРИНГ И ОЧИСТКА ---
    SENTRY_DSN: Optional[str] = None
    CLEANUP_THRESHOLD_DAYS: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()