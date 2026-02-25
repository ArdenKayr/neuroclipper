import asyncio
import os
import sys
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Фикс путей для импорта из соседних папок
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.db_models import Job, User
from models.database import Session
from models.manager import get_or_create_user

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    exit("❌ Ошибка: Токен бота не найден в файле .env!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

URL_PATTERN = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|twitch\.tv|vk\.com|rutube\.ru)/\S+)'

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    status = "👑 Super-User" if user.is_superuser else f"Тариф: {user.subscription_type}"
    await message.answer(
        f"🚀 **NeuroClipper AI**\n\nСтатус: `{status}`\nБаланс: `{user.balance_clips} клипов`\n\n"
        "Пришли ссылку на видео (YouTube, Twitch, VK, Rutube) для начала."
    )

@dp.message(F.text.regexp(URL_PATTERN))
async def handle_link(message: types.Message):
    url = message.text
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⚙️ Начать монтаж (Default)", callback_data=f"proc|{url}"))
    await message.reply("🔗 Ссылка принята! Начинаем работу?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("proc|"))
async def start_processing(callback: types.CallbackQuery):
    url = callback.data.split("|")[1]
    session = Session()
    db_user = session.query(User).filter(User.tg_id == callback.from_user.id).first()
    
    new_job = Job(user_id=db_user.id, input_url=url, priority=1 if db_user.is_superuser else 0)
    session.add(new_job)
    session.commit()
    session.close()

    await callback.message.edit_text("✅ Задача добавлена в очередь. Ожидайте результат!")
    await callback.answer()

async def main():
    print("--- [🤖] Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())