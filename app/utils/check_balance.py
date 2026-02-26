import os
import requests
import asyncio
from aiogram import Bot
from dotenv import load_dotenv
import sys

# Добавляем путь, чтобы скрипт видел модули проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import Session
from models.db_models import User

load_dotenv()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
THRESHOLD = 1.0  # Уведомлять, если меньше $1

async def check_openrouter_balance():
    """Проверяет баланс на OpenRouter и шлет алерт в ТГ при низком остатке"""
    url = "https://openrouter.ai/api/v1/auth/key"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"⚠️ Не удалось проверить баланс (HTTP {response.status_code})")
            return

        data = response.json().get('data', {})
        
        # Безопасное получение значений: если ключ отсутствует или равен None, используем 0
        limit = data.get('limit')
        usage = data.get('usage')
        
        limit_val = float(limit) if limit is not None else 0.0
        usage_val = float(usage) if usage is not None else 0.0
        
        # Если лимит равен 0 и использование 0, возможно это безлимитный ключ или ошибка получения
        if limit_val == 0 and usage_val == 0:
            print("💰 Баланс: Не ограничен или не удалось получить данные")
            return

        credits = limit_val - usage_val
        
        if credits < THRESHOLD:
            print(f"🚨 НИЗКИЙ БАЛАНС: ${credits:.2f}")
            session = Session()
            user = session.query(User).first()
            if user:
                bot = Bot(token=BOT_TOKEN)
                text = (
                    f"🚨 *ВНИМАНИЕ: БАЛАНС ИИ ПОЧТИ ПУСТ*\n\n"
                    f"На счету осталось: *${credits:.2f}*\n"
                    f"Пополни здесь: [OpenRouter](https://openrouter.ai/settings/credits)"
                )
                await bot.send_message(user.tg_id, text, parse_mode="Markdown")
                await bot.session.close()
            session.close()
        else:
            print(f"💰 Баланс в норме: ${credits:.2f}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке баланса: {e}")

if __name__ == "__main__":
    asyncio.run(check_openrouter_balance())