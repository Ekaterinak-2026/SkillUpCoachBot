"""
Планировщик задач бота.
Каждую минуту проверяет, у кого из пользователей наступило
время напоминания в ИХ часовом поясе, и отправляет сообщение.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot

import random
from database import (
    get_all_users,
    get_today_plan,
    get_week_stats,
    days_since_last_activity,
)
from keyboards import (
    step_type_keyboard,
    evening_check_keyboard,
    evening_no_plan_keyboard,
)
import texts

scheduler = AsyncIOScheduler(timezone="UTC")


# ============ ВСПОМОГАТЕЛЬНОЕ ============

def _get_user_tz(user: dict) -> ZoneInfo:
    """Возвращает часовой пояс пользователя или Москву по умолчанию."""
    tz_name = user.get("timezone") or "Europe/Moscow"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("Europe/Moscow")


def _now_hm(tz: ZoneInfo) -> str:
    """Возвращает текущее время в формате ЧЧ:ММ для указанного пояса."""
    return datetime.now(tz).strftime("%H:%M")


def _now_weekday(tz: ZoneInfo) -> int:
    """Возвращает день недели (0 = понедельник, 6 = воскресенье)."""
    return datetime.now(tz).weekday()


# ============ УТРЕННИЕ НАПОМИНАНИЯ ============

async def check_morning(bot: Bot) -> None:
    """Отправляет утренний вопрос тем, у кого наступило время."""
    users = await get_all_users()
    for user in users:
        if not user.get("skill"):
            continue
        tz = _get_user_tz(user)
        if _now_hm(tz) == user.get("morning_time"):
            try:
                await bot.send_message(
                    user["user_id"],
                    texts.MORNING_QUESTION.format(skill=user["skill"]),
                    reply_markup=step_type_keyboard()
                )
            except Exception as e:
                print(f"Ошибка утреннего сообщения {user['user_id']}: {e}")


# ============ ВЕЧЕРНИЕ НАПОМИНАНИЯ ============

async def check_evening(bot: Bot) -> None:
    """Отправляет вечерний чекап тем, у кого наступило время."""
    users = await get_all_users()
    for user in users:
        if not user.get("skill"):
            continue
        tz = _get_user_tz(user)
        if _now_hm(tz) != user.get("evening_time"):
            continue

        plan = await get_today_plan(user["user_id"])
        try:
            if plan:
                await bot.send_message(
                    user["user_id"],
                    texts.EVENING_CHECK.format(
                        step_type=plan["step_type"],
                        skill=user["skill"]
                    ),
                    reply_markup=evening_check_keyboard()
                )
            else:
                await bot.send_message(
                    user["user_id"],
                    texts.EVENING_NO_PLAN.format(skill=user["skill"]),
                    reply_markup=evening_no_plan_keyboard()
                )
        except Exception as e:
            print(f"Ошибка вечернего сообщения {user['user_id']}: {e}")


# ============ ЕЖЕНЕДЕЛЬНЫЙ ДАЙДЖЕСТ ============

async def check_digest(bot: Bot) -> None:
    """Отправляет дайджест по воскресеньям в 18:00 локального времени."""
    users = await get_all_users()
    for user in users:
        if not user.get("skill"):
            continue
        tz = _get_user_tz(user)

        if _now_weekday(tz) != 6:
            continue
        if _now_hm(tz) != "18:00":
            continue

        stats = await get_week_stats(user["user_id"])

        text = texts.DIGEST_HEADER.format(name=user.get("username") or "друг")
        text += texts.DIGEST_BODY.format(
            skill=user["skill"],
            done=stats["done_count"],
            best_streak=user["best_streak"],
            favorite_type=stats["favorite_type"],
            favorite_count=stats["favorite_count"],
            total=user["total_success"]
        )

        if user["best_streak"] >= 5:
            text += texts.DIGEST_TIP_LONG_STREAK.format(streak=user["best_streak"])
        elif stats["done_count"] < 3:
            text += texts.DIGEST_TIP_MANY_MISSES
        else:
            text += texts.DIGEST_TIP_DEFAULT

        try:
            await bot.send_message(user["user_id"], text)
        except Exception as e:
            print(f"Ошибка дайджеста {user['user_id']}: {e}")



# ============ ПОДБАДРИВАЮЩИЕ СООБЩЕНИЯ ============

async def check_nudges(bot: Bot) -> None:
    """Отправляет подбадривающее сообщение пользователям, которые давно не заходили.
    Срабатывает раз в день — в 13:00 локального времени пользователя."""
    users = await get_all_users()
    for user in users:
        if not user.get("skill"):
            continue

        tz = _get_user_tz(user)
        # Отправляем только в 13:00 по локальному времени
        if _now_hm(tz) != "13:00":
            continue

        # Проверяем, сколько дней пользователь не выполнял шаги
        days = await days_since_last_activity(user["user_id"])
        if days < 2 or days == 999:
            continue

        # Выбираем случайную фразу
        template = random.choice(texts.NUDGE_MESSAGES)
        text = template.format(skills=user["skill"])

        try:
            await bot.send_message(user["user_id"], text)
        except Exception as e:
            print(f"Ошибка nudge {user['user_id']}: {e}")


# ============ ЗАПУСК ============

def setup_scheduler(bot: Bot) -> None:
    """Настраивает расписание: проверка каждую минуту."""
    scheduler.add_job(
        check_morning,
        CronTrigger(minute="*", timezone="UTC"),
        args=[bot],
        id="morning_job",
        replace_existing=True
    )
    scheduler.add_job(
        check_evening,
        CronTrigger(minute="*", timezone="UTC"),
        args=[bot],
        id="evening_job",
        replace_existing=True
    )
    scheduler.add_job(
        check_nudges,
        CronTrigger(minute="*", timezone="UTC"),
        args=[bot],
        id="nudge_job",
        replace_existing=True
    )
    scheduler.add_job(
        check_digest,
        CronTrigger(minute="*", timezone="UTC"),
        args=[bot],
        id="digest_job",
        replace_existing=True
    )
    scheduler.start()
    print("Планировщик запущен: проверка каждую минуту по локальному времени")


def shutdown_scheduler() -> None:
    """Останавливает планировщик при выключении бота."""
    if scheduler.running:
        scheduler.shutdown()
        print("Планировщик остановлен")