"""
Обработчики ежедневного цикла:
- Утро: пользователь выбирает тип шага
- Вечер: пользователь отмечает выполнение
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime
from zoneinfo import ZoneInfo

from database import (
    get_user,
    save_daily_plan,
    get_today_plan,
    update_step_status,
    mark_step_done,
    mark_step_failed,
)
from keyboards import step_type_keyboard, evening_check_keyboard
import texts

router = Router()


# ============ УТРО: ВЫБОР ТИПА ШАГА ============

@router.callback_query(F.data.startswith("step:"))
async def process_step_choice(callback: CallbackQuery) -> None:
    """Пользователь выбрал тип шага утром."""
    step_type = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    user = await get_user(user_id)
    if not user or not user.get("skill"):
        await callback.answer("Сначала выбери навык через /start", show_alert=True)
        return

    # Сохраняем план на сегодня
    await save_daily_plan(user_id, step_type)

    # Проверяем: не прошло ли вечернее время в часовом поясе пользователя?
    tz_name = user.get("timezone") or "Europe/Moscow"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Europe/Moscow")

    now_hm = datetime.now(tz).strftime("%H:%M")
    evening_time = user.get("evening_time") or "20:00"

    if now_hm >= evening_time:
        # Вечер уже прошёл — сразу спрашиваем про выполнение
        await callback.message.edit_text(
            f"Отлично! Но вечерний чекап сегодня уже прошёл.\n\n"
            f"Ты успел(а) сделать {step_type} по {user['skill']}?",
            reply_markup=evening_check_keyboard()
        )
    else:
        # Обычный сценарий — ждём вечера
        await callback.message.edit_text(
            texts.MORNING_CONFIRMED.format(
                step_type=step_type,
                skill=user["skill"]
            )
        )
    await callback.answer()


# ============ ВЕЧЕР: ОТВЕТЫ НА ЧЕКАП ============

@router.callback_query(F.data == "evening:done")
async def process_evening_done(callback: CallbackQuery) -> None:
    """Пользователь отметил, что сделал шаг."""
    user_id = callback.from_user.id

    # Отмечаем шаг выполненным
    await update_step_status(user_id, "выполнен")

    # Обновляем серию и получаем новые данные
    user = await mark_step_done(user_id)

    streak = user.get("streak", 0)
    total = user.get("total_success", 0)

    # Если серия кратна 5 — добавляем поздравление
    if streak > 0 and streak % 5 == 0:
        text = texts.STEP_DONE_STREAK_BONUS.format(streak=streak, total=total)
    else:
        text = texts.STEP_DONE.format(streak=streak, total=total)

    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data == "evening:failed")
async def process_evening_failed(callback: CallbackQuery) -> None:
    """Пользователь отметил, что не успел."""
    user_id = callback.from_user.id

    # Сохраняем статус
    await update_step_status(user_id, "пропущен")

    # Запоминаем текущую серию, чтобы показать в сообщении
    old_user = await get_user(user_id)
    old_streak = old_user.get("streak", 0) if old_user else 0

    # Сбрасываем серию
    await mark_step_failed(user_id)

    await callback.message.edit_text(
        texts.STEP_FAILED.format(streak=old_streak)
    )
    await callback.answer()


@router.callback_query(F.data == "evening:postponed")
async def process_evening_postponed(callback: CallbackQuery) -> None:
    """Пользователь переносит шаг на завтра."""
    user_id = callback.from_user.id

    # Сохраняем статус
    await update_step_status(user_id, "перенесён")

    user = await get_user(user_id)
    streak = user.get("streak", 0) if user else 0

    await callback.message.edit_text(
        texts.STEP_POSTPONED.format(streak=streak)
    )
    await callback.answer()


# ============ ВЕЧЕР: ЕСЛИ ПЛАНА НЕ БЫЛО ============

@router.callback_query(F.data == "noplan:now")
async def process_noplan_now(callback: CallbackQuery) -> None:
    """Пользователь решил сделать шаг сейчас (после того, как не выбрал утром)."""
    user_id = callback.from_user.id

    user = await get_user(user_id)
    if not user or not user.get("skill"):
        await callback.answer("Сначала выбери навык через /start", show_alert=True)
        return

    # Считаем это выполненным
    await mark_step_done(user_id)

    user = await get_user(user_id)
    streak = user.get("streak", 0)
    total = user.get("total_success", 0)

    await callback.message.edit_text(
        texts.STEP_DONE.format(streak=streak, total=total)
    )
    await callback.answer()


@router.callback_query(F.data == "noplan:postponed")
async def process_noplan_postponed(callback: CallbackQuery) -> None:
    """Пользователь переносит на завтра (без плана)."""
    user = await get_user(callback.from_user.id)
    streak = user.get("streak", 0) if user else 0

    await callback.message.edit_text(
        texts.STEP_POSTPONED.format(streak=streak)
    )
    await callback.answer()


@router.callback_query(F.data == "noplan:skip")
async def process_noplan_skip(callback: CallbackQuery) -> None:
    """Пользователь пропускает день."""
    await callback.message.edit_text(texts.STEP_SKIPPED)
    await callback.answer()
    # ============ ВЫБОР СТАРТА ============

@router.callback_query(F.data == "start:now")
async def process_start_now(callback: CallbackQuery) -> None:
    """Пользователь хочет начать прямо сейчас — присылаем первый шаг."""
    user = await get_user(callback.from_user.id)
    if not user or not user.get("skill"):
        await callback.answer("Сначала выбери навык через /start", show_alert=True)
        return

    await callback.message.edit_text(
        texts.START_NOW_CONFIRMED + "\n\n" +
        texts.MORNING_QUESTION.format(skill=user["skill"]),
        reply_markup=step_type_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "start:today")
async def process_start_today(callback: CallbackQuery) -> None:
    """Пользователь хочет начать сегодня в назначенное время."""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    await callback.message.edit_text(
        texts.START_TODAY_CONFIRMED.format(morning_time=user["morning_time"])
    )
    await callback.answer()


@router.callback_query(F.data == "start:tomorrow")
async def process_start_tomorrow(callback: CallbackQuery) -> None:
    """Пользователь хочет начать завтра."""
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    await callback.message.edit_text(
        texts.START_TOMORROW_CONFIRMED.format(morning_time=user["morning_time"])
    )
    await callback.answer()