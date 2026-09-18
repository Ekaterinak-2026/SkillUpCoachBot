"""
Работа с базой данных SQLite.
Хранит пользователей и их ежедневные шаги.
Используем aiosqlite для асинхронной работы.
"""

import aiosqlite
from datetime import datetime, timedelta
from typing import Optional

DB_NAME = "skillup.db"


# ============ ИНИЦИАЛИЗАЦИЯ ============

async def init_db() -> None:
    """Создаёт таблицы при первом запуске бота."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                skill TEXT,
                timezone TEXT DEFAULT 'Europe/Moscow',
                morning_time TEXT DEFAULT '09:00',
                evening_time TEXT DEFAULT '20:00',
                streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                total_success INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                step_type TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Миграция: добавляем колонку timezone, если её нет
        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Europe/Moscow'"
            )
        except Exception:
            pass  # Колонка уже существует

        await db.commit()

# ============ ПОЛЬЗОВАТЕЛИ ============

async def add_user(user_id: int, username: str) -> None:
    """Добавляет нового пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()


async def get_user(user_id: int) -> Optional[dict]:
    """Возвращает данные пользователя или None."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_user_skill(user_id: int, skill: str) -> None:
    """Обновляет навык пользователя и сбрасывает серию."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET skill = ?, streak = 0 WHERE user_id = ?",
            (skill, user_id)
        )
        await db.commit()


async def update_user_time(user_id: int, morning: str = None, evening: str = None) -> None:
    """Обновляет время уведомлений."""
    async with aiosqlite.connect(DB_NAME) as db:
        if morning:
            await db.execute(
                "UPDATE users SET morning_time = ? WHERE user_id = ?",
                (morning, user_id)
            )
        if evening:
            await db.execute(
                "UPDATE users SET evening_time = ? WHERE user_id = ?",
                (evening, user_id)
            )
            
        await db.commit()
        
async def update_user_timezone(user_id: int, timezone: str) -> None:
    """Обновляет часовой пояс пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET timezone = ? WHERE user_id = ?",
            (timezone, user_id)
        )
        await db.commit()

async def get_all_users() -> list[dict]:
    """Возвращает всех пользователей (для рассылки по расписанию)."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ============ ЕЖЕДНЕВНЫЕ ШАГИ ============

async def save_daily_plan(user_id: int, step_type: str) -> None:
    """Сохраняет утренний план (тип шага на сегодня)."""
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        # Если план уже был — обновляем
        await db.execute(
            "DELETE FROM daily_steps WHERE user_id = ? AND date = ?",
            (user_id, today)
        )
        await db.execute(
            "INSERT INTO daily_steps (user_id, date, step_type, status) "
            "VALUES (?, ?, ?, 'запланирован')",
            (user_id, today, step_type)
        )
        await db.commit()


async def get_today_plan(user_id: int) -> Optional[dict]:
    """Возвращает план на сегодня."""
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM daily_steps WHERE user_id = ? AND date = ? "
            "ORDER BY id DESC LIMIT 1",
            (user_id, today)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_step_status(user_id: int, status: str) -> None:
    """Обновляет статус сегодняшнего шага (выполнен/пропущен/перенесён)."""
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE daily_steps SET status = ? WHERE user_id = ? AND date = ?",
            (status, user_id, today)
        )
        await db.commit()


# ============ СЕРИЯ И СТАТИСТИКА ============

async def mark_step_done(user_id: int) -> dict:
    """
    Отмечает шаг выполненным, увеличивает серию и total_success.
    Возвращает обновлённые данные пользователя.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        # Увеличиваем серию и total_success
        await db.execute(
            "UPDATE users SET "
            "streak = streak + 1, "
            "total_success = total_success + 1 "
            "WHERE user_id = ?",
            (user_id,)
        )
        # Обновляем best_streak, если текущая серия больше
        await db.execute(
            "UPDATE users SET best_streak = streak "
            "WHERE user_id = ? AND streak > best_streak",
            (user_id,)
        )
        await db.commit()
        # Возвращаем обновлённые данные
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}


async def mark_step_failed(user_id: int) -> dict:
    """Сбрасывает серию, но сохраняет best_streak."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE users SET streak = 0 WHERE user_id = ?", (user_id,)
        )
        await db.commit()
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {}


async def get_week_stats(user_id: int) -> dict:
    """
    Считает статистику за последние 7 дней.
    Возвращает: количество выполненных, любимый тип шага.
    """
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        # Сколько выполнено
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM daily_steps "
            "WHERE user_id = ? AND status = 'выполнен' AND date >= ?",
            (user_id, week_ago)
        ) as cursor:
            row = await cursor.fetchone()
            done_count = row["cnt"] if row else 0

        # Любимый тип шага (самый частый среди выполненных)
        async with db.execute(
            "SELECT step_type, COUNT(*) as cnt FROM daily_steps "
            "WHERE user_id = ? AND status = 'выполнен' AND date >= ? "
            "GROUP BY step_type ORDER BY cnt DESC LIMIT 1",
            (user_id, week_ago)
        ) as cursor:
            row = await cursor.fetchone()
            favorite_type = row["step_type"] if row else "—"
            favorite_count = row["cnt"] if row else 0

        return {
            "done_count": done_count,
            "favorite_type": favorite_type,
            "favorite_count": favorite_count,
        }
    async def reset_user(user_id: int) -> None:
     async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM daily_steps WHERE user_id = ?", (user_id,))
        await db.execute(
            "UPDATE users SET skill = NULL, streak = 0, "
            "best_streak = 0, total_success = 0 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
        