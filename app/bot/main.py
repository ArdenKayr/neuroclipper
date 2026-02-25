import asyncio
import os
import sys
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models.db_models import Job, Preset, User  # Берем сами модели
from models.database import Session             # Берем сессию для работы с БД
from models.manager import get_or_create_user   # Берем логику регистрации

# Добавляем путь к корню, чтобы видеть модели
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.manager import get_or_create_user
from models.db_models import Session, Job, Preset

API_TOKEN = 'ТВОЙ_ТОКЕН_БОТА'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Регулярное выражение для проверки ссылок (YT, Twitch, VK, Rutube)
URL_PATTERN = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|twitch\.tv|vk\.com|rutube\.ru)/\S+)'

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    status = "👑 Super-User" if user.is_superuser else f"Тариф: {user.subscription_type}"
    
    await message.answer(
        f"🚀 **NeuroClipper AI: Система запущена**\n\n"
        f"Статус: `{status}`\n"
        f"Доступно клипов: `{user.balance_clips}`\n\n"
        "Пришли мне ссылку на видео, и я сделаю из него шедевр."
    )

@dp.message(F.text.regexp(URL_PATTERN))
async def handle_link(message: types.Message):
    """Ловим ссылку и предлагаем выбрать настройки"""
    url = message.text
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    
    # Создаем кнопки с пресетами
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="⚙️ Настройки по умолчанию", 
        callback_data=f"process_default|{url}")
    )
    
    # Тут можно добавить цикл по пресетам пользователя из БД
    # builder.row(types.InlineKeyboardButton(text="Пресет: Алоха", callback_data=...))

    await message.reply(
        "🔗 Ссылка принята! Как будем монтировать?",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("process_default"))
async def start_processing(callback: types.CallbackQuery):
    url = callback.data.split("|")[1]
    user_id = callback.from_user.id
    
    # Добавляем задачу в базу данных (в очередь)
    session = Session()
    db_user = session.query(User).filter(User.tg_id == user_id).first()
    
    new_job = Job(
        user_id=db_user.id,
        input_url=url,
        status='pending',
        priority=1 if db_user.is_superuser else 0
    )
    session.add(new_job)
    session.commit()
    session.close()

    await callback.message.edit_text(
        "✅ **Задача добавлена в очередь!**\n\n"
        "ИИ-директор уже анализирует контент. Я пришлю результат, как только всё будет готово."
    )
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())