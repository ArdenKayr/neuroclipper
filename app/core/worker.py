import time
import sys
import os
import asyncio
import logging
from dotenv import load_dotenv

# Настройка путей для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_jobs():
    """Диспетчер задач: передает ссылки из базы в облачные API"""
    analyzer = AIAnalyzer()
    renderer = VideoRenderer()
    
    print("--- [🚀] Диспетчер NEUROCLIPPER запущен (API Mode)...")
    
    while True:
        session = Session()
        job = session.query(Job).filter(Job.status == 'pending').first()
        
        if job:
            print(f"--- [⚙️] Обработка ссылки: {job.input_url} (ID #{job.id})")
            job.status = 'processing'
            session.commit()
            
            try:
                # 1. Поиск хайлайтов через Twelve Labs
                highlights = analyzer.find_visual_highlights(job.input_url)
                
                if highlights:
                    for i, h in enumerate(highlights):
                        print(f"--- [🎬] Отправка в Creatomate: {h['title']}")
                        
                        # 2. Запуск облачного рендеринга
                        # Рендерер сам отправит запрос и вернет ID задачи
                        render_id = renderer.create_short(
                            video_url=job.input_url,
                            start_time=h['start'],
                            end_time=h['end'],
                            title=h['title'],
                            job_id=job.id
                        )
                        
                        if render_id:
                            print(f"✅ Рендер запущен: {render_id}")
                    
                    # Статус 'processing' остается, пока Webhook не пришлет 'done'
                else:
                    job.status = 'no_highlights'

            except Exception as e:
                print(f"--- [❌] Ошибка диспетчера: {e}")
                job.status = 'error'
            
            session.commit()
        
        session.close()
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(process_jobs())