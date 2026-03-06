import logging
from celery_app import app as celery_app
from models.database import Session
from models.db_models import Job
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="process_video_job")
def process_video_job(self, job_id):
    """Единая точка входа для обработки видео в фоне"""
    session = Session()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            return "Job not found"

        job.status = 'processing'
        session.commit()

        analyzer = AIAnalyzer()
        renderer = VideoRenderer()

        # Анализ возвращает хайлайты и ссылку на S3
        highlights, local_file, s3_url = analyzer.find_visual_highlights(job.input_url, job.id)

        if highlights and s3_url:
            total_clips = len(highlights)
            for i, clip in enumerate(highlights):
                is_last = (i == total_clips - 1)
                
                renderer.create_short(
                    s3_url=s3_url,
                    start_time=clip['start'],
                    end_time=clip['end'],
                    title=clip.get('title', f"Highlight {i+1}"),
                    job_id=job.id,
                    local_filename=local_file,
                    is_last=is_last
                )
            logger.info(f"✅ Задача #{job_id} успешно распределена на {total_clips} клипов")
            return f"Processed {total_clips} clips"
        else:
            job.status = 'error'
            session.commit()
            return "No highlights found or upload failed"

    except Exception as e:
        logger.error(f"❌ Критическая ошибка Celery: {e}")
        if 'job' in locals():
            job.status = 'error'
            session.commit()
        raise e
    finally:
        session.close()