import time
import sys
import os
import asyncio
import logging
from aiogram import Bot
from aiogram.types import FSInputFile
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job, User
from services.downloader import VideoDownloader
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))

async def process_jobs():
    dl = VideoDownloader()
    analyzer = AIAnalyzer(model_size="base")
    renderer = VideoRenderer()
    
    print("--- [🚀] Конвейер NEUROCLIPPER (OpenRouter Edition) запущен...")
    
    while True:
        session = Session()
        job = session.query(Job).filter(Job.status == 'pending').first()
        
        if job:
            print(f"--- [⚙️] Задача #{job.id} в работе")
            job.status = 'processing'
            session.commit()
            
            try:
                file_path = dl.download(job.input_url, f"source_{job.id}")
                
                # Используем "зрение" через OpenRouter
                highlights = analyzer.find_visual_highlights(file_path)
                
                if highlights:
                    # Whisper работает локально
                    segments = analyzer.transcribe(file_path)
                    
                    for i, h in enumerate(highlights):
                        clip_path = renderer.create_short(
                            input_path=file_path,
                            segments=segments,
                            start_time=h['start'],
                            end_time=h['end'],
                            title=h['title'],
                            output_name=f"clip_{job.id}_{i}"
                        )
                        
                        user = session.query(User).filter(User.id == job.user_id).first()
                        if user:
                            video_file = FSInputFile(clip_path)
                            await bot.send_video(
                                user.tg_id, 
                                video_file, 
                                caption=f"✨ Клип #{i+1}\n📌 {h['title']}\n\n💡 {h.get('reason', '')}"
                            )
                    
                    job.status = 'done'
                else:
                    job.status = 'no_highlights'
            except Exception as e:
                print(f"--- [❌] Ошибка: {e}")
                job.status = 'error'
            
            session.commit()
        
        session.close()
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(process_jobs())