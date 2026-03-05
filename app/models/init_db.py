import sys
import os

# Добавляем путь к папке app, чтобы Python видел наши модели
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import engine
from models.db_models import Base

def init_db():
    print("--- [🏗️] Начинаю создание таблиц в PostgreSQL...")
    try:
        # SQLAlchemy сама создаст таблицы в той БД, которая указана в DATABASE_URL
        Base.metadata.create_all(bind=engine)
        print("--- [✅] Таблицы созданы успешно: users, presets, channels, jobs")
    except Exception as e:
        print(f"--- [❌] Ошибка при инициализации в Postgres: {e}")

if __name__ == "__main__":
    init_db()