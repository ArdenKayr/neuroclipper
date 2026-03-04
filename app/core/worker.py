import time
import logging
import os
from models.database import Session
from models.db_models import Job
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_jobs():
    analyzer = AIAnalyzer()
    renderer = VideoRenderer()
    
    logger.info("--- [🚀] Диспетчер NEUROCLIPPER запущен...")

    while True:
        session = Session()
        try:
            # Ищем задачу со статусом 'pending'
            job = session.query(Job).filter(Job.status == 'pending').first()
            
            if job:
                job.status = 'processing'
                session.commit()
                
                # ИСПРАВЛЕНО: используем job.input_url, как в db_models.py
                logger.info(f"--- [⚙️] Обработка ссылки: {job.input_url} (ID #{job.id})")

                # 1. Анализ через Twelve Labs. 
                # Теперь возвращает список моментов и путь к скачанному файлу.
                highlights, local_file = analyzer.find_visual_highlights(job.input_url)

                if highlights and local_file:
                    best_clip = highlights[0]
                    
                    # 2. Рендеринг в Creatomate.
                    # Передаем путь к локальному файлу, чтобы рендерер сделал публичную ссылку.
                    render_id = renderer.create_short(
                        local_filename=local_file,
                        start_time=best_clip['start'],
                        end_time=best_clip['end'],
                        title=best_clip['title'],
                        job_id=job.id
                    )
                    
                    if render_id:
                        logger.info(f"✅ Задача #{job.id} отправлена на рендер. ID: {render_id}")
                    else:
                        job.status = 'error'
                else:
                    logger.warning(f"⚠️ Не удалось подготовить видео для задачи #{job.id}")
                    job.status = 'error'

                session.commit()
            else:
                time.sleep(5)

        except Exception as e:
            logger.error(f"❌ Критическая ошибка в цикле воркера: {e}")
            if 'job' in locals() and job:
                job.status = 'error'
                session.commit()
        finally:
            session.close()

if __name__ == "__main__":
    process_jobs()