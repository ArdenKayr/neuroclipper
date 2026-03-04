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
        # Ищем одну задачу со статусом 'pending'
        job = session.query(Job).filter(Job.status == 'pending').first()
        
        if job:
            try:
                job.status = 'processing'
                session.commit()
                logger.info(f"--- [⚙️] Обработка ссылки: {job.video_url} (ID #{job.id})")

                # 1. Анализ через Twelve Labs (теперь возвращает и путь к файлу)
                # Мы немного изменили analyzer, чтобы он возвращал highlights
                highlights = analyzer.find_visual_highlights(job.video_url)

                if highlights:
                    # Берем самый лучший (первый) хайлайт для теста
                    best_clip = highlights[0]
                    
                    # 2. Рендеринг в Creatomate
                    # ВАЖНО: Мы передаем job.id, чтобы Webhook знал, кому ответить
                    render_id = renderer.create_short(
                        video_url=job.video_url, # Или локальный путь, если настроил статику
                        start_time=best_clip['start'],
                        end_time=best_clip['end'],
                        title=best_clip['title'],
                        job_id=job.id
                    )
                    
                    if render_id:
                        logger.info(f"✅ Видео #{job.id} ушло на финальную сборку")
                    else:
                        job.status = 'error'
                else:
                    logger.warning("⚠️ Хайлайты не найдены")
                    job.status = 'error'

                session.commit()

            except Exception as e:
                logger.error(f"❌ Ошибка диспетчера: {e}")
                job.status = 'error'
                session.commit()
        
        session.close()
        time.sleep(10) # Проверка базы каждые 10 секунд

if __name__ == "__main__":
    process_jobs()