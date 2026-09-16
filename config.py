"""
Загрузка конфигурации из .env файла.
Здесь мы получаем токен бота и другие переменные окружения.
"""

import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

# Получаем токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверка, что токен вообще есть
if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден. Создай файл .env в корне проекта "
        "и добавь строку: BOT_TOKEN=твой_токен"
    )

# Часовой пояс (по умолчанию — Москва)
TIMEZONE = "Europe/Moscow"

# Название файла БД
DB_NAME = "skillup.db"