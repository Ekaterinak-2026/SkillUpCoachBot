"""
Планировщик задач бота.
Отправляет утренние и вечерние сообщения по расписанию,
а также еженедельный дайджест по воскресеньям.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from aiogram import Bot

from database import get_all_users, save_daily_plan, get_today_plan, get_week_stats
from keyboards import step_type_keyboard, evening_check_keyboard, evening_no_plan_keyboard
import texts

# Часовой пояс
TIMEZONE = "Europe/Moscow"

# Глобальный планировщик
scheduler = AsyncIOScheduler(timezone=TIMEZONE)


# ============ УТРЕННЯЯ РАССЫЛКА ============

async def send_morning_messages(bot: Bot) -> None:
    """Отправляет утренний вопрос всем пользователям."""
    users = await get_all_users()
    for user in users:
        if not user.get("skill"):
            continue  # пропускаем тех, кто не выбрал навык
        try:
            await bot.send_message(
                user["user_id"],
                texts.MORNING_QUESTION.format(skill=user["skill"]),
                reply_markup=step_type_keyboard()
            )
        except Exception as e:
            print(f"Ошибка отправки утреннего сообщения {user['user_id']}: {e}")


# ============ ВЕЧЕРНЯЯ РАССЫЛКА ============

async def send_evening_messages(bot: Bot) -> None:
    """Отправляет вечерний чекап всем пользователям."""
    users = await get_all_users()
    for user in users:
        if not user.get("skill"):
            continue

        # Проверяем, был ли утренний план
        plan = await get_today_plan(user["user_id"])

        try:
            if plan:
                # План был — спрашиваем про выполнение
                await bot.send_message(
                    user["user_id"],
                    texts.EVENING_CHECK.format(
                        step_type=plan["step_type"],
                        skill=user["skill"]
                    ),
                    reply_markup=evening_check_keyboard()
                )
            else:
                # Плана не было
                await bot.send_message(
                    user["user_id"],
                    texts.EVENING_NO_PLAN.format(skill=user["skill"]),
                    reply_markup=evening_no_plan_keyboard()
                )
        except Exception as e:
            print(f"Ошибка отправки вечернего сообщения {user['user_id']}: {e}")


# ============ ЕЖЕНЕДЕЛЬНЫЙ ДАЙДЖЕСТ ============

async def send_weekly_digest(bot: Bot) -> None:
    """Отправляет недельный дайджест всем пользователям (воскресенье, 18:00)."""
    users = await get_all_users()
    for user in users:
        if not user.get("skill"):
            continue

        stats = await get_week_stats(user["user_id"])

        # Формируем текст дайджеста
        text = texts.DIGEST_HEADER.format(name=user.get("username") or "друг")
        text += texts.DIGEST_BODY.format(
            skill=user["skill"],
            done=stats["done_count"],
            best_streak=user["best_streak"],
            favorite_type=stats["favorite_type"],
            favorite_count=stats["favorite_count"],
            total=user["total_success"]
        )

        # Добавляем совет
        if user["best_streak"] >= 5:
            text += texts.DIGEST_TIP_LONG_STREAK.format(streak=user["best_streak"])
        elif stats["done_count"] < 3:
            text += texts.DIGEST_TIP_MANY_MISSES
        else:
            text += texts.DIGEST_TIP_DEFAULT

        try:
            await bot.send_message(user["user_id"], text)
        except Exception as e:
            print(f"Ошибка отправки дайджеста {user['user_id']}: {e}")


# ============ ЗАПУСК ПЛАНИРОВЩИКА ============

def setup_scheduler(bot: Bot) -> None:
    """
    Настраивает расписание:
    - Утро: каждый день в 9:00
    - Вечер: каждый день в 20:00
    - Дайджест: воскресенье в 18:00
    """
    # Утренний вопрос
    scheduler.add_job(
        send_morning_messages,
        CronTrigger(hour=9, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="morning_job",
        replace_existing=True
    )

    # Вечерний чекап
    scheduler.add_job(
        send_evening_messages,
        CronTrigger(hour=20, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="evening_job",
        replace_existing=True
    )

    # Дайджест (воскресенье)
    scheduler.add_job(
        send_weekly_digest,
        CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=TIMEZONE),
        args=[bot],
        id="digest_job",
        replace_existing=True
    )

    scheduler.start()
    print("Планировщик запущен: утро 9:00, вечер 20:00, дайджест вс 18:00")


def shutdown_scheduler() -> None:
    """Останавливает планировщик при выключении бота."""
    if scheduler.running:
        scheduler.shutdown()
        print("Планировщик остановлен")