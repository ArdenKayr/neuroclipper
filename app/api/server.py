from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os
import json
import logging
from aiogram import Bot
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Session
from models.db_models import Job, User

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(title="Neuroclipper API Receiver")
bot = Bot(token=os.getenv("BOT_TOKEN"))

class WebhookData(BaseModel):
    status: str
    url: str = None  # Ссылка на готовое видео от Creatomate
    metadata: str = None  # Наша запакованная строка с job_id и title

@app.post("/webhook/update-job")
async def update_job(data: WebhookData):
    """Принимает сигнал о готовности и отправляет видео в ТГ"""
    session = Session()
    try:
        # Распаковываем метаданные
        if not data.metadata:
            raise HTTPException(status_code=400, detail="Metadata missing")
            
        meta = json.loads(data.metadata)
        job_id = meta.get("job_id")
        clip_title = meta.get("title", "Твой клип")

        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Creatomate использует статус 'succeeded' для успеха
        if data.status == "succeeded" and data.url:
            job.status = 'done'
            user = session.query(Session).filter(User.id == job.user_id).first()
            if user:
                await bot.send_video(
                    user.tg_id, 
                    data.url, 
                    caption=f"✅ *{clip_title}*\n\nГотово через облачный рендеринг!"
                )
        elif data.status == "failed":
            job.status = 'error'
            
        session.commit()
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Ошибка Webhook: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)