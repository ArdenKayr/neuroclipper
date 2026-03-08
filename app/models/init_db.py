import sys
import os
import asyncio

# Добавляем путь к папке app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import engine
from models.db_models import Base

async def init_db():
    print("--- [🏗️] Начинаю создание таблиц в PostgreSQL (Async)...")
    try:
        async with engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)
        print("--- [✅] Таблицы созданы успешно: users, transaction_logs, presets, channels, jobs")
    except Exception as e:
        print(f"--- [❌] Ошибка при инициализации в Postgres: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())