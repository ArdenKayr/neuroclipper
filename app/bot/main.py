import asyncio
import os
import sys
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from dotenv import load_dotenv

# Настройка путей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tasks import process_video_job
from models.db_models import Job, User
from models.database import Session
from models.manager import get_or_create_user

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не найден")
    sys.exit(1)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
URL_PATTERN = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|twitch\.tv|vk\.com|rutube\.ru)/\S+)'

def get_main_keyboard():
    """Главное нижнее меню (Reply Keyboard)"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="✂️ Нарезать видео")
    builder.button(text="👤 Мой профиль")
    builder.button(text="🆘 Поддержка")
    builder.adjust(2, 1) # Две кнопки в первом ряду, одна во втором
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Онбординг пользователя"""
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    
    welcome_text = (
        "👋 **Добро пожаловать в Neuroclipper AI!**\n\n"
        "Я нейросеть, которая автоматически находит лучшие моменты в твоих длинных видео (YouTube/Twitch) "
        "и превращает их в виральные Shorts/Reels с трендовыми субтитрами.\n\n"
        f"🎁 Тебе начислено **{user.balance_clips} бесплатных клипов** для теста.\n\n"
        "Выбери действие в меню ниже 👇"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(F.text == "👤 Мой профиль")
async def show_profile(message: types.Message):
    """Личный кабинет пользователя"""
    session = Session()
    db_user = session.query(User).filter(User.tg_id == message.from_user.id).first()
    
    if not db_user:
        db_user = get_or_create_user(message.from_user.id, message.from_user.username)

    status = "👑 ВЛАДЕЛЕЦ" if db_user.is_superuser else f"Тариф: {db_user.subscription_type.upper()}"
    
    # Считаем историю заказов
    jobs_count = session.query(Job).filter(Job.user_id == db_user.id).count()
    session.close()

    profile_text = (
        "👤 **Твой профиль:**\n\n"
        f"🏷 {status}\n"
        f"💎 Баланс: `{db_user.balance_clips} клипов`\n"
        f"📊 Обработано видео: `{jobs_count}`\n\n"
        "*(Скоро здесь появится кнопка пополнения баланса)*"
    )
    await message.answer(profile_text, parse_mode="Markdown")

@dp.message(F.text == "🆘 Поддержка")
async def show_support(message: types.Message):
    """Раздел помощи"""
    support_text = (
        "🛠 **Поддержка Neuroclipper**\n\n"
        "• Бот поддерживает ссылки на YouTube, Twitch, VK Видео.\n"
        "• Видео должно быть не короче 5 минут и не длиннее 3 часов.\n"
        "• Среднее время нарезки 1 часа видео — около 5-7 минут.\n\n"
        "Если что-то сломалось, пиши админу: @ТвойЮзернейм"
    )
    await message.answer(support_text, parse_mode="Markdown")

@dp.message(F.text == "✂️ Нарезать видео")
async def request_link(message: types.Message):
    """Просьба прислать ссылку"""
    await message.answer(
        "🔗 Пришли мне ссылку на длинное видео (YouTube, Twitch, VK).\n"
        "Я проанализирую его и нарежу самые виральные моменты!"
    )

@dp.message(F.text.regexp(URL_PATTERN))
async def handle_link(message: types.Message):
    """Обработка ссылки и выбор стиля (Воронка создания)"""
    url = message.text
    session = Session()
    db_user = session.query(User).filter(User.tg_id == message.from_user.id).first()
    
    if db_user.balance_clips <= 0 and not db_user.is_superuser:
        await message.answer("❌ У тебя закончились клипы на балансе. Пожалуйста, пополни счет.")
        session.close()
        return

    # Создаем Job со статусом 'pending'
    new_job = Job(user_id=db_user.id, input_url=url, priority=1 if db_user.is_superuser else 0)
    session.add(new_job)
    session.commit()
    job_id = new_job.id
    session.close()

    # Предлагаем выбрать стиль
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔥 Динамичный (Желтые сабы)", callback_data=f"style|{job_id}|dynamic"))
    builder.row(types.InlineKeyboardButton(text="🎬 Минимализм (Белые сабы)", callback_data=f"style|{job_id}|minimal"))
    
    await message.reply(
        "✅ Ссылка принята!\n\nВыберите визуальный стиль для ваших Shorts:", 
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data.startswith("style|"))
async def start_processing_with_style(callback: types.CallbackQuery):
    """Запуск Celery-задачи после выбора стиля"""
    _, job_id, style = callback.data.split("|")
    
    # Вызываем воркер
    process_video_job.delay(int(job_id), style) 

    style_name = "Динамичный" if style == "dynamic" else "Минимализм"
    await callback.message.edit_text(
        f"⏳ **Задача #{job_id} запущена!**\n\n"
        f"🎨 Стиль: `{style_name}`\n\n"
        "Бот начал скачивание и анализ. Вы можете закрыть чат, я пришлю уведомление, когда видео будут готовы."
        , parse_mode="Markdown"
    )
    await callback.answer()

async def main():
    print("--- [🤖] Бот NEUROCLIPPER v2 запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())