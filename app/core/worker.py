import time
import sys
import os

# Фикс путей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job
from services.downloader import VideoDownloader

def process_jobs():
    dl = VideoDownloader()
    print("--- [⚒️] Воркер запущен и ищет задачи...")
    
    while True:
        session = Session()
        # Ищем одну задачу со статусом pending, сначала с высоким приоритетом
        job = session.query(Job).filter(Job.status == 'pending').order_by(Job.priority.desc()).first()
        
        if job:
            print(f"--- [📥] Найдена задача {job.id}: {job.input_url}")
            job.status = 'downloading'
            session.commit()
            
            # Скачиваем
            file_path = dl.download(job.input_url, f"video_{job.id}")
            
            if file_path:
                print(f"--- [✅] Видео скачано в {file_path}. Начинаем монтаж (в разработке)...")
                job.status = 'done' # Пока ставим done, когда напишем монтаж - заменим
            else:
                job.status = 'error'
            
            session.commit()
        
        session.close()
        time.sleep(5) # Спим 5 секунд перед следующей проверкой

if __name__ == "__main__":
    process_jobs()