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
app.mount("/static", StaticFiles(directory="/root/neuroclipper/temp_videos"), name="static")
bot = Bot(token=os.getenv("BOT_TOKEN"))

class WebhookData(BaseModel):
    status: str
    url: str = None
    metadata: str = None

@app.post("/webhook/update-job")
async def update_job(data: WebhookData):
    """Принимает сигнал от Creatomate и пересылает видео в Telegram"""
    logger.info(f"--- [📩] Получен Webhook! Статус: {data.status}")
    
    session = Session()
    try:
        if not data.metadata:
            logger.warning("⚠️ Webhook пришел без метаданных")
            return {"status": "ignored"}
            
        meta = json.loads(data.metadata)
        job_id = meta.get("job_id")
        
        # 1. Ищем задачу в базе
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"❌ Задача #{job_id} не найдена в БД")
            return {"status": "error", "message": "Job not found"}

        # 2. Если видео готово (статус 'succeeded' в Creatomate)
        if data.status == "succeeded" and data.url:
            logger.info(f"✅ Видео для задачи #{job_id} готово: {data.url}")
            
            # ИСПРАВЛЕНО: Правильный запрос к таблице User
            user = session.query(User).filter(User.id == job.user_id).first()
            
            if user:
                try:
                    await bot.send_video(
                        user.tg_id, 
                        data.url, 
                        caption=f"🎬 *Твой клип готов!*\n\nID задачи: {job_id}\nСтатус: Успешно",
                        parse_mode="Markdown"
                    )
                    job.status = 'done'
                    logger.info(f"🚀 Видео отправлено пользователю @{user.tg_id}")
                except Exception as tg_err:
                    logger.error(f"❌ Ошибка отправки в TG: {tg_err}")
            else:
                logger.error(f"❌ Пользователь для задачи #{job_id} не найден")

        session.commit()
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка Webhook: {e}")
        return {"status": "error"}
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)