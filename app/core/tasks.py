import logging
import os
import asyncio
import sentry_sdk
from datetime import datetime, timedelta
from celery_app import app as celery_app
from models.database import Session
from models.db_models import Job
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer
from core.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=1.0)

logger = logging.getLogger(__name__)

async def _async_process_job(job_id: int, preset_style: str):
    """Асинхронная обертка для выполнения всего пайплайна"""
    session = Session()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job: return "Job not found"

        job.status = 'processing'
        session.commit()

        analyzer = AIAnalyzer()
        renderer = VideoRenderer()

        # Шаг 1: Анализ (с предыдущего шага)
        highlights, local_file, s3_url = await analyzer.find_visual_highlights(job.input_url, job.id)

        # Шаг 2: Рендеринг и Визуал (текущий шаг)
        if highlights and s3_url:
            for i, clip in enumerate(highlights):
                # Эмулируем получение reframe-координат из хайлайта
                reframe_data = {"scale": "140%", "x": "45%"} 
                
                await renderer.create_short(
                    s3_url=s3_url,
                    start_time=clip['start'],
                    end_time=clip['end'],
                    title=clip.get('title', f"Highlight {i+1}"),
                    job_id=job.id,
                    local_filename=local_file,
                    style=preset_style, # Передаем UI Пресет
                    reframe_data=reframe_data, # Передаем Auto-Reframe
                    is_last=(i == len(highlights) - 1)
                )
            return f"Processed {len(highlights)} clips"
        
        job.status = 'error'
        session.commit()
        return "Failed to analyze"
    finally:
        session.close()

@celery_app.task(bind=True, name="process_video_job", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_video_job(self, job_id, preset_style="dynamic"):
    """Синхронная Celery-задача, запускающая асинхронный пайплайн"""
    return asyncio.run(_async_process_job(job_id, preset_style))

@celery_app.task(name="cleanup_old_files")
def cleanup_old_files():
    download_dir = "assets/downloads"
    if not os.path.exists(download_dir):
        return "Directory not found"
        
    now = datetime.now()
    count = 0
    for f in os.listdir(download_dir):
        f_path = os.path.join(download_dir, f)
        if os.stat(f_path).st_mtime < (now - timedelta(days=settings.CLEANUP_THRESHOLD_DAYS)).timestamp():
            os.remove(f_path)
            count += 1
    return f"Removed {count} old files"