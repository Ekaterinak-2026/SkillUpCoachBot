"""
Точка входа бота SkillUp Coach.
Запускает бота, подключает обработчики, инициализирует БД и планировщик.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database import init_db
from scheduler import setup_scheduler, shutdown_scheduler

# Импортируем роутеры из handlers
from handlers import start, daily, commands, digest


# ============ ЛОГИРОВАНИЕ ============

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)
async def set_commands(bot: Bot) -> None:
    """Устанавливает постоянное меню команд в интерфейсе Telegram."""
    commands = [
        BotCommand(command="start", description="Начать и выбрать навык"),
        BotCommand(command="stats", description="Мой прогресс"),
        BotCommand(command="settings", description="Настройки"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Меню команд установлено")

# ============ ЗАПУСК ============

async def main() -> None:
    """Главная функция: инициализация и запуск бота."""
    logger.info("Запуск SkillUp Coach...")

    # 1. Инициализируем базу данных
    await init_db()
    logger.info("База данных готова")

    # 2. Создаём бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # 3. Подключаем роутеры (порядок важен!)
    dp.include_router(start.router)
    dp.include_router(daily.router)
    dp.include_router(commands.router)
    dp.include_router(digest.router)
    logger.info("Роутеры подключены")

    # 3.5. Устанавливаем меню команд
    await set_commands(bot)
    
    # 4. Запускаем планировщик
    setup_scheduler(bot)

    # 5. Запускаем polling
    logger.info("Бот запущен. Нажми Ctrl+C для остановки.")
    try:
        await dp.start_polling(bot)
    finally:
        # Корректно останавливаем планировщик
        shutdown_scheduler()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем.")