import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from services.validator import LinkValidator
from models.database import AsyncSessionLocal
from models.db_models import User, Job
from sqlalchemy import select
from core.tasks import process_video_job

router = Router()
logger = logging.getLogger(__name__)
validator = LinkValidator(max_duration_seconds=10800) # 3 часа

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    async with AsyncSessionLocal() as session:
        # Простая регистрация пользователя
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(tg_id=message.from_user.id, username=message.from_user.username, balance_clips=5)
            session.add(user)
            await session.commit()
            await message.answer("👋 Привет! Я Neuroclipper. Я помогу нарезать длинные видео в Shorts.\n\nТебе начислено 5 бесплатных клипов. Просто пришли мне ссылку на YouTube видео (до 3 часов).")
        else:
            await message.answer(f"С возвращением! Твой баланс: {user.balance_clips} клипов. Присылай ссылку.")

@router.message(F.text.contains("youtube.com") | F.text.contains("youtu.be"))
async def handle_link(message: types.Message):
    url = message.text.strip()
    
    # 1. Визуальный статус
    status_msg = await message.answer("🔍 Проверяю ссылку...")

    # 2. Валидация (Шаг 2.1)
    is_valid, error, metadata = await validator.validate_video(url)
    
    if not is_valid:
        await status_msg.edit_text(f"❌ Ошибка: {error}")
        return

    # 3. Проверка баланса и создание задачи
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user or user.balance_clips <= 0:
            await status_msg.edit_text("💳 Недостаточно клипов на балансе.")
            return

        # Создаем запись о задаче
        new_job = Job(user_id=user.id, input_url=url, status='pending')
        session.add(new_job)
        await session.flush() # Получаем ID задачи
        
        # Списываем баланс (логика будет расширена в 4.1)
        user.balance_clips -= 1
        await session.commit()
        
        job_id = new_job.id

    await status_msg.edit_text(f"✅ Видео «{metadata['title']}» принято!\n⏳ Длительность: {metadata['duration'] // 60} мин.\n\nНачинаю обработку... [⏳ Скачивание...]")
    
    # 4. Отправка в Celery (Воркер подхватит задачу)
    process_video_job.delay(job_id, preset_style="dynamic")