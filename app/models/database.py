from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Путь к базе данных (в корне проекта)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'neuroclipper.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)