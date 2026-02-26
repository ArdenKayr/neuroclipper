import os
import requests
import asyncio
from aiogram import Bot
from dotenv import load_dotenv
import sys

# Добавляем путь, чтобы скрипт видел базу данных и конфиги
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import Session
from models.db_models import User

load_dotenv()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
THRESHOLD = 1.0  # Порог уведомления в долларах

async def check_openrouter_balance():
    url = "https://openrouter.ai/api/v1/auth/key"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Получаем текущий баланс (credits)
        # В OpenRouter API баланс часто отображается в ключе 'data'
        credits = data.get('data', {}).get('limit', 0) - data.get('data', {}).get('usage', 0)
        
        if credits < THRESHOLD:
            print(f"⚠️ Внимание: Низкий баланс! Осталось: ${credits:.2f}")
            
            # Берем первого пользователя из базы, чтобы знать кому слать
            session = Session()
            user = session.query(User).first()
            
            if user:
                bot = Bot(token=BOT_TOKEN)
                message = (
                    f"🚨 *ВНИМАНИЕ: БАЛАНС ИИ ПОЧТИ ПУСТ*\n\n"
                    f"На счету OpenRouter осталось: *${credits:.2f}*\n"
                    f"Этого может не хватить на следующие задачи.\n\n"
                    f"Пополни здесь: [OpenRouter Credits](https://openrouter.ai/settings/credits)"
                )
                await bot.send_message(user.tg_id, message, parse_mode="Markdown")
                await bot.session.close()
            session.close()
        else:
            print(f"💰 Баланс в норме: ${credits:.2f}")
            
    except Exception as e:
        print(f"❌ Ошибка проверки баланса: {e}")

if __name__ == "__main__":
    asyncio.run(check_openrouter_balance())