import logging
import asyncio
import os
from celery_app import app as celery_app
from sqlalchemy import select
from models.database import AsyncSessionLocal
from models.db_models import Job, User
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer
from aiogram import Bot
from aiogram.types import FSInputFile
from core.config import settings

logger = logging.getLogger(__name__)
bot = Bot(token=settings.BOT_TOKEN)

async def _async_process_job(job_id: int):
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Job, User).join(User, Job.user_id == User.id).where(Job.id == job_id)
            )
            data = result.first()
            if not data: return
            job, user = data

            analyzer = AIAnalyzer()
            # Находим моменты (уже работает через GPT-4o)
            highlights, local_raw_path, _ = await analyzer.find_visual_highlights(job.input_url, job.id)

            if not highlights or not local_raw_path:
                raise Exception("Анализ не удался")

            renderer = VideoRenderer()
            for i, clip in enumerate(highlights[:3]): # Берем 3 для теста
                final_path = await renderer.create_short(
                    local_video_path=local_raw_path,
                    start_time=clip['start'],
                    end_time=clip['end'],
                    title=clip.get('title', 'Clip'),
                    job_id=job.id
                )

                if final_path and os.path.exists(final_path):
                    video_file = FSInputFile(final_path)
                    await bot.send_video(
                        chat_id=user.tg_id, 
                        video=video_file, 
                        caption=f"🎬 **Клип №{i+1}**\n📌 {clip.get('title')}"
                    )
                    os.remove(final_path)

            if os.path.exists(local_raw_path):
                os.remove(local_raw_path)

            job.status = 'completed'
            await session.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка задачи {job_id}: {e}")

@celery_app.task(name="process_video_job")
def process_video_job(job_id):
    return asyncio.run(_async_process_job(job_id))