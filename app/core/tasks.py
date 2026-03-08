import logging
import os
import asyncio
import sentry_sdk
from datetime import datetime, timedelta
from celery_app import app as celery_app
from sqlalchemy import select

from models.database import AsyncSessionLocal
from models.db_models import Job
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer
from core.config import settings
from services.cleanup import CleanupService

# Инициализация Sentry для отслеживания ошибок в воркерах
if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=1.0)

logger = logging.getLogger(__name__)

async def _async_process_job(job_id: int, preset_style: str):
    """
    Асинхронная обертка для выполнения всего пайплайна:
    Скачивание -> Анализ -> Рендеринг
    """
    async with AsyncSessionLocal() as session:
        try:
            # Получаем задачу из БД
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            
            if not job:
                logger.error(f"❌ Задача #{job_id} не найдена в базе данных")
                return "Job not found"

            # Обновляем статус
            job.status = 'processing'
            await session.commit()

            analyzer = AIAnalyzer()
            renderer = VideoRenderer()

            logger.info(f"--- [⚙️] Начало обработки задачи #{job_id}: {job.input_url}")

            # Шаг 1: Анализ (Скачивание + Поиск хайлайтов)
            highlights, local_file, s3_url = await analyzer.find_visual_highlights(job.input_url, job.id)

            # Шаг 2: Рендеринг и Визуал
            if highlights and s3_url:
                total_clips = len(highlights)
                logger.info(f"✅ Найдено хайлайтов: {total_clips}. Запуск рендеринга...")
                
                for i, clip in enumerate(highlights):
                    # Эмулируем получение reframe-координат (в будущем от Vizard)
                    reframe_data = {"scale": "140%", "x": "45%"} 
                    
                    await renderer.create_short(
                        s3_url=s3_url,
                        start_time=clip['start'],
                        end_time=clip['end'],
                        title=clip.get('title', f"Highlight {i+1}"),
                        job_id=job.id,
                        local_filename=local_file,
                        style=preset_style,
                        reframe_data=reframe_data,
                        is_last=(i == total_clips - 1)
                    )
                
                return f"Processed {total_clips} clips"
            
            # Если хайлайты не найдены
            job.status = 'error'
            job.error_message = "No highlights found or download failed"
            await session.commit()
            logger.warning(f"⚠️ Не удалось обработать задачу #{job_id}")
            return "Failed to analyze"

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при обработке задачи #{job_id}: {e}")
            if job:
                job.status = 'error'
                job.error_message = str(e)
                await session.commit()
            return str(e)

@celery_app.task(bind=True, name="process_video_job", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_video_job(self, job_id, preset_style="dynamic"):
    """Синхронная Celery-задача, запускающая асинхронный пайплайн обработки видео"""
    return asyncio.run(_async_process_job(job_id, preset_style))

@celery_app.task(name="cleanup_old_files")
def cleanup_old_files():
    """
    Регулярная задача для очистки старых файлов:
    1. Локальные файлы в assets/downloads
    2. Объекты в Cloudflare R2
    """
    try:
        cleaner = CleanupService()
        local_deleted, s3_deleted = cleaner.run_full_cleanup()
        return f"Cleanup successful: removed {local_deleted} local files and {s3_deleted} S3 objects"
    except Exception as e:
        logger.error(f"❌ Ошибка в задаче очистки: {e}")
        return f"Cleanup failed: {e}"