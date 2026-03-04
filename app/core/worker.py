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
    # Инициализируем наши инструменты
    analyzer = AIAnalyzer()
    renderer = VideoRenderer()
    
    logger.info("--- [🚀] Диспетчер NEUROCLIPPER запущен...")

    while True:
        session = Session()
        try:
            # Ищем задачу со статусом 'pending'
            job = session.query(Job).filter(Job.status == 'pending').first()
            
            if job:
                # Меняем статус на 'processing', чтобы другие воркеры её не хватали
                job.status = 'processing'
                session.commit()
                
                # ИСПРАВЛЕНО: используем job.url вместо job.video_url
                logger.info(f"--- [⚙️] Обработка ссылки: {job.url} (ID #{job.id})")

                # 1. Анализ через Twelve Labs (скачивание и поиск хайлайтов)
                highlights = analyzer.find_visual_highlights(job.url)

                if highlights:
                    # Берем первый найденный хайлайт
                    best_clip = highlights[0]
                    
                    # 2. Рендеринг в Creatomate
                    # Мы передаем job.url и job.id для Webhook-связи
                    render_id = renderer.create_short(
                        video_url=job.url,
                        start_time=best_clip['start'],
                        end_time=best_clip['end'],
                        title=best_clip['title'],
                        job_id=job.id
                    )
                    
                    if render_id:
                        logger.info(f"✅ Задача #{job.id} успешно отправлена на рендер!")
                    else:
                        logger.error(f"❌ Ошибка при отправке задачи #{job.id} в Creatomate")
                        job.status = 'error'
                else:
                    logger.warning(f"⚠️ Twelve Labs не нашел хайлайтов для задачи #{job.id}")
                    job.status = 'error'

                session.commit()

            else:
                # Если задач нет, просто ждем
                pass

        except Exception as e:
            logger.error(f"❌ Критическая ошибка в цикле воркера: {e}")
            if 'job' in locals() and job:
                job.status = 'error'
                session.commit()
        
        finally:
            session.close()
            
        time.sleep(5) # Спим 5 секунд перед следующей проверкой базы

if __name__ == "__main__":
    process_jobs()