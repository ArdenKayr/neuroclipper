import logging
import asyncio
import os
from celery_app import app as celery_app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models.db_models import Job, User
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer
from aiogram import Bot
from aiogram.types import FSInputFile
from core.config import settings

logger = logging.getLogger(__name__)

async def _async_process_job(job_id: int):
    db_url = settings.DATABASE_URL
    if db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    local_engine = create_async_engine(db_url, pool_pre_ping=True)
    LocalSession = async_sessionmaker(bind=local_engine, expire_on_commit=False)
    
    bot = Bot(token=settings.BOT_TOKEN)

    try:
        async with LocalSession() as session:
            result = await session.execute(
                select(Job, User).join(User, Job.user_id == User.id).where(Job.id == job_id)
            )
            data = result.first()
            if not data: return
            job, user = data

            status_msg = await bot.send_message(
                chat_id=user.tg_id, 
                text="⏳ **Видео скачано!**\nСлушаю аудио и ищу виральные моменты через ИИ...", 
                parse_mode="Markdown"
            )

            analyzer = AIAnalyzer()
            highlights, local_raw_path, _ = await analyzer.find_visual_highlights(job.input_url, job.id)

            if not highlights or not local_raw_path:
                await bot.edit_message_text(
                    "❌ Не удалось проанализировать видео. Возможно, там нет речи.",
                    chat_id=user.tg_id, message_id=status_msg.message_id
                )
                raise Exception("Анализ не удался")

            await bot.edit_message_text(
                f"✅ **Найдено {len(highlights)} хайлайтов!**\nНачинаю нарезку, поиск B-Rolls и рендер...",
                chat_id=user.tg_id, message_id=status_msg.message_id, parse_mode="Markdown"
            )

            renderer = VideoRenderer()
            for i, clip in enumerate(highlights[:3]):
                final_path = await renderer.create_short(
                    local_video_path=local_raw_path,
                    start_time=clip['start'],
                    end_time=clip['end'],
                    title=clip.get('title', f'Clip {i+1}'),
                    job_id=job.id,
                    b_roll_query=clip.get('b_roll_query')  # 🔥 ПЕРЕДАЕМ ЗАПРОС НА B-ROLL
                )

                if final_path and os.path.exists(final_path):
                    video_file = FSInputFile(final_path)
                    caption = f"🎬 **Клип №{i+1}**\n📌 {clip.get('title')}"
                    if clip.get('reason'):
                        caption += f"\n💡 {clip.get('reason')}"
                        
                    await bot.send_video(
                        chat_id=user.tg_id, 
                        video=video_file, 
                        caption=caption
                    )
                    os.remove(final_path)

            if os.path.exists(local_raw_path):
                os.remove(local_raw_path)

            job.status = 'completed'
            await session.commit()
            
    except Exception as e:
        logger.error(f"❌ Ошибка задачи {job_id}: {e}")
        try:
            if 'user' in locals():
                await bot.send_message(user.tg_id, "⚠️ Произошла ошибка при обработке видео.")
        except Exception:
            pass
    finally:
        await local_engine.dispose()
        await bot.session.close()

@celery_app.task(name="process_video_job")
def process_video_job(job_id):
    return asyncio.run(_async_process_job(job_id))