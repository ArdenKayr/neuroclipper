from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .db_models import User

# Указываем путь к базе
engine = create_engine("sqlite:///neuroclipper.db")
Session = sessionmaker(bind=engine)

def get_or_create_user(tg_id, username):
    session = Session()
    try:
        user = session.query(User).filter(User.tg_id == tg_id).first()
        if not user:
            # Первый зашедший в бот становится владельцем (SuperUser)
            is_first = session.query(User).count() == 0
            user = User(
                tg_id=tg_id, 
                username=username, 
                is_superuser=is_first,
                subscription_type='agency' if is_first else 'нарезчик',
                balance_clips=999999 if is_first else 0
            )
            session.add(user)
            session.commit()
            print(f"--- [👤] Новый пользователь: {username} (SuperUser: {is_first})")
        return user
    finally:
        session.close()
