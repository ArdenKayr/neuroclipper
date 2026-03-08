import asyncio
import os
import sys
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Настройка путей, чтобы Python видел папку app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tasks import process_video_job
from models.db_models import Job, User
from models.database import Session
from models.manager import get_or_create_user

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не найден в файле .env")
    sys.exit(1)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
URL_PATTERN = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|twitch\.tv|vk\.com|rutube\.ru)/\S+)'

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    status = "👑 ВЛАДЕЛЕЦ" if user.is_superuser else f"Тариф: {user.subscription_type}"
    await message.answer(
        f"🚀 **NEUROCLIPPER AI (v2.0)**\n\n"
        f"Статус: `{status}`\n"
        f"Баланс: `{user.balance_clips} клипов`\n\n"
        "Пришли ссылку на длинное видео (YouTube, Twitch), чтобы нарезать виральные Shorts."
    )

@dp.message(F.text.regexp(URL_PATTERN))
async def handle_link(message: types.Message):
    url = message.text
    session = Session()
    db_user = session.query(User).filter(User.tg_id == message.from_user.id).first()
    
    # 1. Создаем Job со статусом 'pending'
    new_job = Job(user_id=db_user.id, input_url=url, priority=1 if db_user.is_superuser else 0)
    session.add(new_job)
    session.commit()
    job_id = new_job.id
    session.close()

    # 2. Предлагаем выбрать стиль (Пресет)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔥 Динамичный (Hormozi style)", callback_data=f"style|{job_id}|dynamic"))
    builder.row(types.InlineKeyboardButton(text="🎬 Минимализм (Cinematic)", callback_data=f"style|{job_id}|minimal"))
    builder.row(types.InlineKeyboardButton(text="🎮 Гейминг (Facecam + Gameplay)", callback_data=f"style|{job_id}|gaming"))
    
    await message.reply(
        "🔗 Ссылка принята!\n\nВыберите стиль монтажа для ваших Shorts:", 
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("style|"))
async def start_processing_with_style(callback: types.CallbackQuery):
    _, job_id, style = callback.data.split("|")
    
    # Запускаем фоновую задачу Celery, передавая выбранный стиль
    process_video_job.delay(int(job_id), style) 

    await callback.message.edit_text(f"✅ Задача #{job_id} запущена!\nВыбран стиль: `{style}`.\nОжидайте готовые видео.")
    await callback.answer()

async def main():
    print("--- [🤖] Бот NEUROCLIPPER v2 запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 