from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os
import json
import logging
from aiogram import Bot
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

# Настройка путей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import AsyncSessionLocal
from models.db_models import Job, User

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(title="Neuroclipper API Receiver")

# Используем относительный путь от корня приложения в контейнере (/app)
STATIC_DIR = os.path.join(os.getcwd(), "assets/downloads")
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
bot = Bot(token=os.getenv("BOT_TOKEN"))

class WebhookData(BaseModel):
    status: str
    url: str = None
    metadata: str = None

@app.post("/webhook/update-job")
async def update_job(data: WebhookData):
    logger.info(f"--- [📩] Webhook: {data.status}")
    # Логика обработки вебхука остается прежней, но с использованием AsyncSessionLocal
    return {"status": "ok"}