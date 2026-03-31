from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_NAME: str
    S3_PUBLIC_URL: str

    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: Optional[str] = None # 🔥 Добавили поддержку прокси
    CREATOMATE_API_KEY: str
    CREATOMATE_TEMPLATE_ID: str
    CAPTIONS_API_KEY: Optional[str] = None
    
    ENABLE_VIZARD: bool = False
    VIZARD_API_KEY: Optional[str] = None
    TWELVE_LABS_API_KEY: Optional[str] = None
    
    SENTRY_DSN: Optional[str] = None
    CLEANUP_THRESHOLD_DAYS: int = 1

    WEBHOOK_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()