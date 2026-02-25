import asyncio
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Магия путей, чтобы бот видел папку models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.manager import get_or_create_user

API_TOKEN = 'ТВОЙ_ТОКЕН_ТУТ'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Регистрируем или получаем юзера
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    
    role = "👑 ВЛАДЕЛЕЦ (SuperUser)" if user.is_superuser else f"Тариф: {user.subscription_type}"
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        f"Твой статус: **{role}**\n"
        f"Остаток клипов: {user.balance_clips}\n\n"
        "Отправь мне ссылку на видео (Twitch, YT, VK, Rutube), чтобы начать."
    )

async def main():
    print("--- [🤖] Бот NeuroClipper запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
