import logging
import json
from fastapi import FastAPI, Request, BackgroundTasks
from aiogram import Bot
from core.config import settings
from models.database import AsyncSessionLocal
from models.db_models import Job, User
from sqlalchemy import select

logger = logging.getLogger(__name__)
app = FastAPI(title="Neuroclipper API Result Listener")
bot = Bot(token=settings.BOT_TOKEN)

async def send_video_to_user(job_id: int, video_url: str, title: str):
    """Фоновая задача для отправки видео пользователю в Telegram"""
    async with AsyncSessionLocal() as session:
        # 1. Ищем задачу и пользователя
        result = await session.execute(
            select(Job, User).join(User, Job.user_id == User.id).where(Job.id == job_id)
        )
        job_user = result.first()
        
        if not job_user:
            logger.error(f"❌ Webhook: Задача #{job_id} не найдена в базе.")
            return

        job, user = job_user

        try:
            # 2. Отправляем видео в Telegram (по ссылке, чтобы не качать на свой сервер)
            caption = f"🎬 **Ваш клип готов!**\n\n📌 {title}\n\n#neuroclip"
            await bot.send_video(
                chat_id=user.tg_id,
                video=video_url,
                caption=caption,
                parse_mode="Markdown"
            )
            logger.info(f"--- [📤] Видео из задачи #{job_id} отправлено пользователю @{user.username}")
            
            # 3. Обновляем статус задачи
            job.status = 'completed'
            await session.commit()
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки видео в Telegram: {e}")

@app.post("/webhook/creatomate")
async def creatomate_webhook(request: Request, background_tasks: BackgroundTasks):
    """Принимает уведомление от Creatomate о завершении рендера"""
    try:
        data = await request.json()
        # В Creatomate статус завершения - 'succeeded'
        status = data.get('status')
        
        if status == 'succeeded':
            render_id = data.get('id')
            video_url = data.get('url')
            
            # Извлекаем наши метаданные, которые мы передавали в renderer.py
            metadata_str = data.get('metadata', '{}')
            metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
            
            job_id = metadata.get('job_id')
            title = metadata.get('title', 'Ваш хайлайт')

            if job_id:
                logger.info(f"--- [✅] Рендер {render_id} завершен для задачи #{job_id}")
                background_tasks.add_task(send_video_to_user, int(job_id), video_url, title)
            
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Ошибка в обработчике Webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    return {"status": "alive"}