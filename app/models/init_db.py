import sys
import os
from sqlalchemy import create_engine

# Добавляем текущую директорию в путь поиска, чтобы увидеть db_models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_models import Base

# База будет лежать в корне проекта ~/neuroclipper/neuroclipper.db
DATABASE_URL = "sqlite:///../../neuroclipper.db"

def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("--- [✅] База данных NeuroClipper успешно создана!")

if __name__ == "__main__":
    init_db()
