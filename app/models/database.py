import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Берем URL из .env. В Postgres не нужен BASE_DIR для пути к файлу.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не найден в .env. Проверь настройки!")

# Настройки для PostgreSQL: 
# pool_size — сколько соединений держать открытыми
# max_overflow — сколько временных соединений можно создать сверху
engine = create_engine(
    DATABASE_URL, 
    pool_size=10, 
    max_overflow=20,
    pool_pre_ping=True # Проверяет живое ли соединение перед использованием
)

Session = sessionmaker(bind=engine)