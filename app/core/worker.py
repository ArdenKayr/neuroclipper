import time
import sys
import os
import json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job
from services.downloader import VideoDownloader
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer

def process_jobs():
    dl = VideoDownloader()
    analyzer = AIAnalyzer(model_size="base")
    renderer = VideoRenderer()
    
    print("--- [🚀] Конвейер NEUROCLIPPER запущен...")
    
    while True:
        session = Session()
        job = session.query(Job).filter(Job.status == 'pending').first()
        
        if job:
            job.status = 'processing'
            session.commit()
            
            # 1. Загрузка
            file_path = dl.download(job.input_url, f"source_{job.id}")
            
            if file_path:
                # 2. Анализ
                segments = analyzer.transcribe(file_path)
                highlights = analyzer.find_highlights(segments)
                
                # 3. Нарезка (берем первый найденный хайлайт для теста)
                if highlights:
                    h = highlights[0]
                    clip_path = renderer.create_short(
                        file_path, h['start'], h['end'], h['text'], f"result_{job.id}"
                    )
                    print(f"--- [✨] Готово! Клип сохранен: {clip_path}")
                    job.status = 'done'
                else:
                    print("--- [🤷] Хайлайты не найдены.")
                    job.status = 'no_highlights'
            else:
                job.status = 'error'
            
            session.commit()
        session.close()
        time.sleep(5)

if __name__ == "__main__":
    process_jobs()