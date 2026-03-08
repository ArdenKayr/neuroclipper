import asyncio
import logging
import sentry_sdk
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from core.config import settings

# Инициализация мониторинга Sentry (Шаг 1.4)
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("--- [🤖] Запуск Telegram бота Neuroclipper V2.3 (Async)...")
    
    # Инициализация бота и диспетчера
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # В будущем здесь будут подключаться роутеры из Шага 3.3
    # Например:
    # from bot.handlers import base_router
    # dp.include_router(base_router)

    try:
        # Удаляем вебхуки, если они были, и запускаем long polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка при работе бота: {e}")
    finally:
        await bot.session.close()
        logger.info("--- [🔌] Сессия бота закрыта.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("--- [🛑] Бот остановлен вручную.")