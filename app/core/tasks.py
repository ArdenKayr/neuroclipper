import logging
import asyncio
import sentry_sdk
from celery_app import app as celery_app
from sqlalchemy import select
from models.database import AsyncSessionLocal
from models.db_models import Job
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer
from core.config import settings
from services.cleanup import CleanupService

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=1.0)

logger = logging.getLogger(__name__)

async def _async_process_job(job_id: int, preset_style: str):
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job: return "Job not found"

            job.status = 'processing'
            await session.commit()

            analyzer = AIAnalyzer()
            renderer = VideoRenderer()

            # ШАГ 1: Анализ (Whisper/Сабы + Claude)
            highlights, local_file, s3_url = await analyzer.find_visual_highlights(job.input_url, job.id)

            if highlights and s3_url:
                total = len(highlights)
                logger.info(f"🚀 Запускаю рендер {total} клипов...")
                
                for i, clip in enumerate(highlights):
                    await renderer.create_short(
                        s3_url=s3_url,
                        start_time=clip['start'],
                        end_time=clip['end'],
                        title=clip.get('title', 'Moment'),
                        job_id=job.id,
                        local_filename=local_file,
                        style=preset_style,
                        is_last=(i == total - 1)
                    )
                return f"OK: {total} clips in progress"

            job.status = 'error'
            job.error_message = "Analysis failed"
            await session.commit()
            return "Failed"

        except Exception as e:
            logger.error(f"❌ Ошибка в задаче {job_id}: {e}")
            return str(e)

@celery_app.task(bind=True, name="process_video_job", max_retries=1)
def process_video_job(self, job_id, preset_style="dynamic"):
    return asyncio.run(_async_process_job(job_id, preset_style))

@celery_app.task(name="cleanup_old_files")
def cleanup_old_files():
    cleaner = CleanupService()
    return cleaner.run_full_cleanup()