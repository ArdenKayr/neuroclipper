import logging
from celery_app import app as celery_app
from models.database import Session
from models.db_models import Job
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="process_video_job")
def process_video_job(self, job_id):
    """Фоновая задача по обработке видео"""
    session = Session()
    job = session.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        return "Job not found"

    try:
        job.status = 'processing'
        session.commit()
        
        logger.info(f"--- [⚙️] Celery обрабатывает задачу ID #{job_id}")

        analyzer = AIAnalyzer()
        renderer = VideoRenderer()

        # Анализ (скачивание + ИИ)
        highlights, local_file = analyzer.find_visual_highlights(job.input_url)

        if highlights and local_file:
            total_clips = len(highlights)
            for i, clip in enumerate(highlights):
                is_last = (i == total_clips - 1)
                
                renderer.create_short(
                    local_filename=local_file,
                    start_time=clip['start'],
                    end_time=clip['end'],
                    title=clip.get('title', f"Highlight {i+1}"),
                    job_id=job.id,
                    is_last=is_last
                )
            return f"Success: {total_clips} clips sent to render"
        else:
            job.status = 'error'
            session.commit()
            return "No highlights found"

    except Exception as e:
        logger.error(f"❌ Ошибка в задаче Celery: {e}")
        job.status = 'error'
        session.commit()
        raise e # Celery может перезапустить задачу при ошибке
    finally:
        session.close()