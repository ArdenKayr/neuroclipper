import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from services.validator import LinkValidator
from models.database import AsyncSessionLocal
from models.db_models import User, Job
from sqlalchemy import select
from core.tasks import process_video_job, dub_video_job

router = Router()
logger = logging.getLogger(__name__)
validator = LinkValidator(max_duration_seconds=10800) # 3 часа

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user:
            # Даем сразу много клипов на всякий случай, хотя списывать их пока не будем
            user = User(tg_id=message.from_user.id, username=message.from_user.username, balance_clips=9999)
            session.add(user)
            await session.commit()
            await message.answer("👋 Привет! Я Neuroclipper. Я помогу нарезать длинные видео в Shorts.\n\nСейчас бот работает в **БЕЗЛИМИТНОМ тестовом режиме**. Просто пришли мне ссылку на YouTube видео (до 3 часов).", parse_mode="Markdown")
        else:
            await message.answer("С возвращением! Бот работает в **БЕЗЛИМИТНОМ тестовом режиме**. Присылай ссылку на видео.", parse_mode="Markdown")

@router.message(F.text.contains("youtube.com") | F.text.contains("youtu.be"))
async def handle_link(message: types.Message):
    url = message.text.strip()
    
    status_msg = await message.answer("🔍 Проверяю ссылку...")

    is_valid, error, metadata = await validator.validate_video(url)
    
    if not is_valid:
        await status_msg.edit_text(f"❌ Ошибка: {error}")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        # Если юзер не нажимал /start, регаем его на лету
        if not user:
            user = User(tg_id=message.from_user.id, username=message.from_user.username, balance_clips=9999)
            session.add(user)
            await session.flush()
        
        # --- ВРЕМЕННО ОТКЛЮЧЕНО НА ВРЕМЯ ТЕСТОВ ---
        # if user.balance_clips <= 0:
        #     await status_msg.edit_text("💳 Недостаточно клипов на балансе.")
        #     return

        new_job = Job(user_id=user.id, input_url=url, status='pending')
        session.add(new_job)
        await session.flush() 
        
        # --- ВРЕМЕННО ОТКЛЮЧЕНО НА ВРЕМЯ ТЕСТОВ ---
        # user.balance_clips -= 1
        
        await session.commit()
        
        job_id = new_job.id

    await status_msg.edit_text(f"✅ Видео «{metadata['title']}» принято!\n⏳ Длительность: {metadata['duration'] // 60} мин.\n\nНачинаю обработку... [⏳ Скачивание...]")
    
    process_video_job.delay(job_id)


# --- ОБРАБОТЧИК КНОПКИ ДАББИНГА ---
@router.callback_query(F.data.startswith("dub_"))
async def handle_dub_callback(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) != 4:
        return await callback.answer("❌ Ошибка данных", show_alert=True)
        
    job_id = int(parts[1])
    start_time = float(parts[2])
    end_time = float(parts[3])
    
    await callback.message.answer("🇺🇸 Отлично! Запускаю нейросети для перевода и американской озвучки...\nЭто займет пару минут. ⏳")
    await callback.answer()
    
    dub_video_job.delay(job_id, start_time, end_time, callback.from_user.id)