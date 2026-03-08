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
    CREATOMATE_API_KEY: str
    CREATOMATE_TEMPLATE_ID: str
    VIZARD_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    CAPTIONS_API_KEY: Optional[str] = None
    TWELVE_LABS_API_KEY: Optional[str] = None
    
    # --- МОНИТОРИНГ ---
    SENTRY_DSN: Optional[str] = None
    
    # --- НАСТРОЙКИ ОЧИСТКИ ---
    CLEANUP_THRESHOLD_DAYS: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()   