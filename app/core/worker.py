import time
import sys
import os
import asyncio
import logging
from aiogram import Bot
from aiogram.types import FSInputFile
from dotenv import load_dotenv

# Настройка путей, чтобы Python видел папки проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job, User
from services.downloader import VideoDownloader
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer

# Загружаем переменные окружения
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_jobs():
    dl = VideoDownloader()
    # Analyzer теперь умеет и в Whisper, и в Gemini
    analyzer = AIAnalyzer(model_size="base")
    renderer = VideoRenderer()
    
    print("--- [🚀] Конвейер NEUROCLIPPER (Vision Edition) запущен...")
    
    while True:
        session = Session()
        # Ищем задачу, которую еще не трогали
        job = session.query(Job).filter(Job.status == 'pending').first()
        
        if job:
            print(f"--- [⚙️] Начинаю работу над задачей #{job.id}")
            job.status = 'processing'
            session.commit()
            
            try:
                # 1. СКАЧИВАНИЕ
                file_path = dl.download(job.input_url, f"source_{job.id}")
                if not file_path:
                    raise Exception("Не удалось скачать видео")

                # 2. ВИЗУАЛЬНЫЙ АНАЛИЗ (Gemini 1.5 Pro)
                # Нейронка смотрит видео и выбирает лучшие моменты
                highlights = analyzer.find_visual_highlights(file_path)
                
                if highlights:
                    # 3. ТРАНСКРИБАЦИЯ (Whisper)
                    # Делаем один раз для всего видео, чтобы наложить титры
                    print(f"--- [👂] Whisper расшифровывает текст...")
                    segments = analyzer.transcribe(file_path)
                    
                    # Обрабатываем каждый найденный Gemini момент
                    for i, h in enumerate(highlights):
                        print(f"--- [🎬] Рендеринг клипа {i+1}/{len(highlights)}: {h['title']}")
                        
                        # 4. РЕНДЕРИНГ
                        # Передаем все 6 аргументов, как просит наш renderer.py
                        clip_path = renderer.create_short(
                            input_path=file_path,
                            segments=segments,      # Танцы с титрами
                            start_time=h['start'],  # Время от Gemini
                            end_time=h['end'],
                            title=h['title'],       # Креативный заголовок
                            output_name=f"clip_{job.id}_{i}"
                        )
                        
                        # 5. ОТПРАВКА В ТЕЛЕГРАМ
                        user = session.query(User).filter(User.id == job.user_id).first()
                        if user:
                            print(f"--- [📤] Отправка видео пользователю {user.tg_id}...")
                            video_file = FSInputFile(clip_path)
                            await bot.send_video(
                                user.tg_id, 
                                video_file, 
                                caption=f"🔥 Клип #{i+1} готов!\n\n📌 {h['title']}\n\n💡 Почему это круто: {h.get('reason', 'Просто хайпово')}"
                            )
                    
                    job.status = 'done'
                else:
                    print("--- [🤷] Gemini не нашла интересных моментов")
                    job.status = 'no_highlights'

            except Exception as e:
                print(f"--- [❌] Ошибка в процессе: {e}")
                job.status = 'error'
            
            session.commit()
        
        session.close()
        # Пауза 5 секунд, чтобы не спамить базу
        await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(process_jobs())
    except KeyboardInterrupt:
        print("\n--- [🛑] Воркер остановлен пользователем")