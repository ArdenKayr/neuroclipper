from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os
import json
import logging
from aiogram import Bot
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

# Пути для импорта моделей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job, User

load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Neuroclipper API Receiver")

# --- ИСПРАВЛЕНИЕ ПУТИ ---
# В Docker мы работаем в /app. Используем папку assets/downloads для статики.
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets/downloads")
os.makedirs(STATIC_DIR, exist_ok=True) # Создаем папку, если ее нет, чтобы избежать RuntimeError

# Раздаем папку с видео
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
bot = Bot(token=os.getenv("BOT_TOKEN"))

class WebhookData(BaseModel):
    status: str
    url: str = None
    metadata: str = None

@app.post("/webhook/update-job")
async def update_job(data: WebhookData):
    """Принимает сигнал от Creatomate, шлет видео и чистит исходники"""
    logger.info(f"--- [📩] Получен Webhook! Статус: {data.status}")
    
    session = Session()
    try:
        if not data.metadata:
            return {"status": "ignored"}
            
        meta = json.loads(data.metadata)
        job_id = meta.get("job_id")
        local_file = meta.get("local_file")
        is_last = meta.get("is_last", False)
        
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"status": "error", "message": "Job not found"}

        # Отправка видео пользователю
        if data.status == "succeeded" and data.url:
            user = session.query(User).filter(User.id == job.user_id).first()
            if user:
                try:
                    await bot.send_video(
                        user.tg_id, 
                        data.url, 
                        caption=f"🎬 *Твой клип готов!*\n\nНазвание: {meta.get('title')}\nID задачи: {job_id}",
                        parse_mode="Markdown"
                    )
                    logger.info(f"🚀 Видео отправлено в Telegram")
                except Exception as tg_err:
                    logger.error(f"❌ Ошибка отправки: {tg_err}")

        # Удаление исходника, если это был последний клип или произошла ошибка
        if (is_last and data.status == "succeeded") or data.status == "failed":
            if local_file and os.path.exists(local_file):
                os.remove(local_file)
                logger.info(f"🗑️ Исходный файл удален: {local_file}")
            
            job.status = 'done' if data.status == "succeeded" else 'error'

        session.commit()
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки вебхука: {e}")
        return {"status": "error"}
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)