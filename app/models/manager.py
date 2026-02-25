from .database import Session
from .db_models import User

def get_or_create_user(tg_id, username):
    session = Session()
    try:
        user = session.query(User).filter(User.tg_id == tg_id).first()
        if not user:
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
            session.refresh(user) # Чтобы подгрузить ID из базы
        return user
    finally:
        session.close()