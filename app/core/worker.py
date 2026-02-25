import time
import sys
import os
import asyncio
import logging
from aiogram import Bot
from dotenv import load_dotenv

# Настройка путей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job, User
from services.downloader import VideoDownloader
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer

# Загружаем токен для отправки видео
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN)

async def process_jobs():
    dl = VideoDownloader()
    analyzer = AIAnalyzer(model_size="base")
    renderer = VideoRenderer()
    
    print("--- [🚀] Конвейер NEUROCLIPPER с авто-отправкой запущен...")
    
    while True:
        session = Session()
        job = session.query(Job).filter(Job.status == 'pending').first()
        
        if job:
            print(f"--- [⚙️] Обработка задачи #{job.id} для пользователя {job.user_id}")
            job.status = 'processing'
            session.commit()
            
            # 1. Загрузка
            file_path = dl.download(job.input_url, f"source_{job.id}")
            
            if file_path:
                # 2. Анализ
                segments = analyzer.transcribe(file_path)
                highlights = analyzer.find_highlights(segments)
                
                if highlights:
                    # Берем самый сочный хайлайт (первый)
                    h = highlights[0]
                    # 3. Рендеринг
                    try:
                        clip_path = renderer.create_short(
                            file_path, h['start'], h['end'], h['text'], f"result_{job.id}"
                        )
                        
                        # 4. ОТПРАВКА В ТЕЛЕГРАМ
                        user = session.query(User).filter(User.id == job.user_id).first()
                        if user:
                            print(f"--- [📤] Отправка видео пользователю {user.tg_id}...")
                            from aiogram.types import FSInputFile
                            video_file = FSInputFile(clip_path)
                            await bot.send_video(
                                user.tg_id, 
                                video_file, 
                                caption=f"🎬 Твой клип готов!\n\nТекст: {h['text']}"
                            )
                        
                        job.status = 'done'
                    except Exception as e:
                        print(f"--- [❌] Ошибка рендеринга/отправки: {e}")
                        job.status = 'error'
                else:
                    print("--- [🤷] Хайлайты не найдены.")
                    job.status = 'no_highlights'
            else:
                job.status = 'error'
            
            session.commit()
        
        session.close()
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(process_jobs())