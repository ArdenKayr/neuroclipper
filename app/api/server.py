from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os
import logging
from aiogram import Bot
from dotenv import load_dotenv

# Настройка путей для импорта моделей из корня проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job, User

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(title="Neuroclipper API Receiver")
bot = Bot(token=os.getenv("BOT_TOKEN"))

class WebhookData(BaseModel):
    job_id: int
    status: str
    video_url: str = None
    title: str = "Твой клип готов!"

@app.post("/webhook/update-job")
async def update_job(data: WebhookData):
    """Принимает сигнал о готовности видео и отправляет его пользователю"""
    session = Session()
    try:
        job = session.query(Job).filter(Job.id == data.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Задача не найдена")

        job.status = data.status
        session.commit()

        if data.status == "done" and data.video_url:
            user = session.query(User).filter(User.id == job.user_id).first()
            if user:
                await bot.send_video(
                    user.tg_id, 
                    data.video_url, 
                    caption=f"✨ *{data.title}*\n\nГотово через облачный рендеринг!"
                )
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Ошибка Webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)