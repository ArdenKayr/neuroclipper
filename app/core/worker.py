import time
import sys
import os
import asyncio
import logging
from aiogram import Bot
from aiogram.types import FSInputFile
from dotenv import load_dotenv

# Настройка путей для импорта модулей приложения
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job, User
from services.downloader import VideoDownloader
from core.analyzer import AIAnalyzer
from core.renderer import VideoRenderer

# Загрузка конфигурации
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN)

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_jobs():
    """Основной цикл воркера по обработке видео-задач"""
    dl = VideoDownloader()
    analyzer = AIAnalyzer(model_size="base")
    renderer = VideoRenderer()
    
    print("--- [🚀] Конвейер NEUROCLIPPER (Gemini 3 Edition) запущен...")
    
    while True:
        session = Session()
        # Берем задачу в статусе 'pending'
        job = session.query(Job).filter(Job.status == 'pending').first()
        
        if job:
            print(f"--- [⚙️] Работаю над задачей #{job.id}")
            job.status = 'processing'
            session.commit()
            
            file_path = None
            try:
                # 1. СКАЧИВАНИЕ (передаем job.id для формирования уникального имени)
                file_path = dl.download(job.input_url, job.id)
                if not file_path:
                    raise Exception("Ошибка при скачивании видео (проверьте URL)")

                # 2. ГЛУБОКИЙ ВИЗУАЛЬНЫЙ АНАЛИЗ (Gemini 3 Flash)
                print(f"--- [👁️] Gemini 3 анализирует сцены в {file_path}...")
                highlights = analyzer.find_visual_highlights(file_path)
                
                if highlights:
                    # 3. ТРАНСКРИБАЦИЯ ДЛЯ ТИТРОВ (Whisper)
                    print(f"--- [👂] Whisper расшифровывает аудио...")
                    segments = analyzer.transcribe(file_path)
                    
                    for i, h in enumerate(highlights):
                        print(f"--- [🎬] Рендеринг клипа {i+1}/{len(highlights)}: {h['title']}")
                        
                        # 4. РЕНДЕРИНГ ВЕРТИКАЛЬНОГО ВИДЕО
                        clip_path = renderer.create_short(
                            input_path=file_path,
                            segments=segments,
                            start_time=h['start'],
                            end_time=h['end'],
                            title=h['title'],
                            output_name=f"clip_{job.id}_{i}_{int(time.time())}"
                        )
                        
                        # 5. ОТПРАВКА В ТЕЛЕГРАМ
                        user = session.query(User).filter(User.id == job.user_id).first()
                        if user:
                            print(f"--- [📤] Отправка ролика пользователю {user.tg_id}...")
                            video_file = FSInputFile(clip_path)
                            
                            # Формируем описание на основе данных от Gemini 3
                            caption = (
                                f"✨ *Клип #{i+1} готов!*\n\n"
                                f"📌 *{h['title']}*\n"
                                f"💡 *Почему это круто:* {h.get('reason', 'Интересный момент')}\n\n"
                                f"🎬 *Что в кадре:* {h.get('visual_description', 'Динамичная сцена')}"
                            )
                            
                            await bot.send_video(
                                user.tg_id, 
                                video_file, 
                                caption=caption,
                                parse_mode="Markdown"
                            )
                    
                    job.status = 'done'
                else:
                    print(f"--- [🤷] Хайлайты не найдены для задачи #{job.id}")
                    job.status = 'no_highlights'

            except Exception as e:
                print(f"--- [❌] Критическая ошибка: {e}")
                job.status = 'error'
            
            finally:
                # 6. ОЧИСТКА (удаляем тяжелый исходник после обработки)
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"--- [🗑️] Исходный файл {file_path} удален.")
                    except Exception as cleanup_error:
                        print(f"--- [⚠️] Не удалось удалить файл: {cleanup_error}")
                
                session.commit()
        
        session.close()
        # Пауза между проверками новых задач
        await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(process_jobs())
    except KeyboardInterrupt:
        print("\n--- [🛑] Воркер остановлен пользователем.")