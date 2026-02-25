import time
import sys
import os
import logging

# Настройка путей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job
from services.downloader import VideoDownloader
from core.analyzer import AIAnalyzer

def process_jobs():
    dl = VideoDownloader()
    # Инициализируем ИИ один раз при запуске
    analyzer = AIAnalyzer(model_size="base")
    
    print("--- [⚒️] Воркер NEUROCLIPPER запущен и готов к ИИ-анализу...")
    
    while True:
        session = Session()
        job = session.query(Job).filter(Job.status == 'pending').order_by(Job.priority.desc()).first()
        
        if job:
            print(f"--- [🚀] Начинаю работу над задачей {job.id}")
            job.status = 'downloading'
            session.commit()
            
            # 1. Скачиваем
            file_path = dl.download(job.input_url, f"video_{job.id}")
            
            if file_path:
                job.status = 'analyzing'
                session.commit()
                
                # 2. ИИ-Анализ
                try:
                    segments = analyzer.transcribe(file_path)
                    highlights = analyzer.find_highlights(segments)
                    
                    # Сохраняем результат в папку с задачей
                    result_path = file_path.replace(".mp4", "_analysis.json")
                    with open(result_path, 'w', encoding='utf-8') as f:
                        import json
                        json.dump(highlights, f, ensure_ascii=False, indent=4)
                    
                    print(f"--- [✨] Анализ завершен! Найдено клипов: {len(highlights)}")
                    job.status = 'done'
                except Exception as e:
                    print(f"--- [❌] Ошибка анализа: {e}")
                    job.status = 'error'
            else:
                job.status = 'error'
            
            session.commit()
        
        session.close()
        time.sleep(5)

if __name__ == "__main__":
    process_jobs()