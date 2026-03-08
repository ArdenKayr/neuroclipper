from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Ключи API ---
    BOT_TOKEN: str
    TWELVE_LABS_API_KEY: str
    CREATOMATE_API_KEY: str
    CREATOMATE_TEMPLATE_ID: str
    OPENROUTER_API_KEY: str
    VIZARD_API_KEY: str = ""  
    OPENAI_API_KEY: str = ""  
    CAPTIONS_API_KEY: str = "" # Новый ключ для динамичных субтитров
    SENTRY_DSN: str = ""

    # --- Базы данных ---
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Cloudflare R2 ---
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_NAME: str = "neuroclipper-files"
    S3_PUBLIC_URL: str

    # --- Настройки проекта ---
    CLEANUP_THRESHOLD_DAYS: int = 2

settings = Settings()