import os
import requests
import asyncio
from aiogram import Bot
from dotenv import load_dotenv
import sys

# Настройка путей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import Session
from models.db_models import User

load_dotenv()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
THRESHOLD = 1.0  # Порог в $1

async def check_openrouter_balance():
    url = "https://openrouter.ai/api/v1/auth/key"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"⚠️ Не удалось проверить баланс (код {response.status_code})")
            return

        data = response.json()
        # Баланс в OpenRouter = лимит - использование
        credits = data.get('data', {}).get('limit', 0) - data.get('data', {}).get('usage', 0)
        
        if credits < THRESHOLD:
            print(f"🚨 НИЗКИЙ БАЛАНС: ${credits:.2f}")
            session = Session()
            user = session.query(User).first()
            if user:
                bot = Bot(token=BOT_TOKEN)
                text = f"🚨 *Внимание!* Баланс OpenRouter: *${credits:.2f}*.\nПора пополнить счет!"
                await bot.send_message(user.tg_id, text, parse_mode="Markdown")
                await bot.session.close()
            session.close()
        else:
            print(f"💰 Баланс: ${credits:.2f} (ОК)")
            
    except Exception as e:
        print(f"❌ Ошибка API: {e}")

if __name__ == "__main__":
    asyncio.run(check_openrouter_balance())