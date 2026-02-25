import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Находим корень проекта, чтобы база лежала в ~/neuroclipper/neuroclipper.db
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'neuroclipper.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)