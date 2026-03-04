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
                
                logger.info(f"--- [⚙️] Обработка ссылки: {job.input_url} (ID #{job.id})")

                # Анализатор возвращает список всех моментов и путь к скачанному файлу
                highlights, local_file = analyzer.find_visual_highlights(job.input_url)

                if highlights and local_file:
                    total_clips = len(highlights)
                    logger.info(f"✅ Найдено хайлайтов: {total_clips}. Начинаю рендеринг всех частей...")
                    
                    for i, clip in enumerate(highlights):
                        # Помечаем последний клип, чтобы сервер знал, когда удалять исходник
                        is_last = (i == total_clips - 1)
                        
                        render_id = renderer.create_short(
                            local_filename=local_file,
                            start_time=clip['start'],
                            end_time=clip['end'],
                            title=clip.get('title', f"Highlight {i+1}"),
                            job_id=job.id,
                            is_last=is_last
                        )
                        
                        if render_id:
                            logger.info(f"  [+] Клип {i+1}/{total_clips} отправлен в Creatomate")
                else:
                    logger.warning(f"⚠️ Хайлайты не найдены для задачи #{job.id}")
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