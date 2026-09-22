"""
Обработчики ежедневного цикла:
- Утро: пользователь выбирает тип шага
- Вечер: пользователь отмечает выполнение
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime
from zoneinfo import ZoneInfo

from database import (
    get_user,
    save_daily_plan,
    save_daily_plan_for_skill,
    get_today_plan,
    get_all_today_plans,
    update_step_status,
    update_step_status_by_skill,
    mark_step_done,
    mark_step_failed,
    get_active_skills,
)
from keyboards import (
    step_type_keyboard,
    evening_check_keyboard,
    start_choice_keyboard,
)
import texts

router = Router()


# ============ УТРО: ВЫБОР ТИПА ШАГА ============

@router.callback_query(F.data.startswith("ms:"))
async def process_morning_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь выбрал тип шага для одного навыка утром."""
    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.answer()
        return

    try:
        skill_id = int(parts[1])
    except ValueError:
        await callback.answer()
        return

    step_type = parts[2]
    user_id = callback.from_user.id

    # Получаем активные навыки
    skills = await get_active_skills(user_id)
    if not skills:
        await callback.answer("Сначала добавь навык через /start", show_alert=True)
        return

    # Сохраняем выбор в FSM
    data = await state.get_data()
    chosen: dict = data.get("morning_chosen", {})
    chosen[str(skill_id)] = step_type
    await state.update_data(morning_chosen=chosen)

    # Ищем следующий непройденный навык
    next_skill = None
    for s in skills:
        if str(s["id"]) not in chosen:
            next_skill = s
            break

    if next_skill:
        # Формируем сообщение с уже выбранными + следующим
        lines = ["☀️ Доброе утро! Выбери шаг на сегодня.", ""]
        for s in skills:
            if str(s["id"]) in chosen:
                lines.append(f"✅ {s['name']} — {chosen[str(s['id'])]}")
        lines.append("")
        lines.append(f"📌 {next_skill['name']}:")

        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=step_type_keyboard(next_skill["id"])
        )
    else:
        # Все навыки пройдены — сохраняем в БД
        for sid_str, st in chosen.items():
            await save_daily_plan_for_skill(user_id, int(sid_str), st)

        lines = ["☀️ План на сегодня:", ""]
        for s in skills:
            lines.append(f"✅ {s['name']} — {chosen[str(s['id'])]}")
        lines.append("")
        lines.append("Поехали! 🚀")

        await callback.message.edit_text("\n".join(lines))
        await state.clear()

    await callback.answer()


# ============ ВЕЧЕР: ОТВЕТЫ НА ЧЕКАП ============

@router.callback_query(F.data.startswith("es:"))
async def process_evening_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка вечернего ответа по одному навыку."""
    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.answer()
        return

    try:
        skill_id = int(parts[1])
    except ValueError:
        await callback.answer()
        return

    action = parts[2]  # done / failed / postponed
    user_id = callback.from_user.id

    # Обновляем статус в БД
    status_map = {
        "done": "выполнен",
        "failed": "пропущен",
        "postponed": "перенесён",
    }
    await update_step_status_by_skill(user_id, skill_id, status_map[action])

    # Сохраняем в FSM
    data = await state.get_data()
    answered: dict = data.get("evening_answered", {})
    answered[str(skill_id)] = action
    await state.update_data(evening_answered=answered)

    # Проверяем: остались ли ещё незавершённые планы?
    plans = await get_all_today_plans(user_id)
    pending = [
        p for p in plans
        if p["status"] == "запланирован"
    ]

    if pending:
        # Есть ещё — показываем следующий
        next_plan = pending[0]
        skill_name = next_plan.get("skill_name") or "навык"
        text = (
            "🌙 Пришло время чекапа.\n\n"
            f"📌 {skill_name} — {next_plan['step_type']}. Получилось?"
        )
        await callback.message.edit_text(
            text,
            reply_markup=evening_check_keyboard(next_plan["skill_id"])
        )
    else:
        # Все ответы получены — считаем серию
        user = await get_user(user_id)
        any_done = any(a == "done" for a in answered.values())

        if any_done:
            user = await mark_step_done(user_id)
            streak = user.get("streak", 0)
            total = user.get("total_success", 0)

            if streak > 0 and streak % 5 == 0:
                text = texts.STEP_DONE_STREAK_BONUS.format(streak=streak, total=total)
            else:
                text = texts.STEP_DONE.format(streak=streak, total=total)
        else:
            old = await get_user(user_id)
            old_streak = old.get("streak", 0) if old else 0
            await mark_step_failed(user_id)
            text = texts.STEP_FAILED.format(streak=old_streak)

        await callback.message.edit_text(text)
        await state.clear()

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
async def process_start_now(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь хочет начать прямо сейчас — присылаем первый навык."""
    user_id = callback.from_user.id
    skills = await get_active_skills(user_id)

    if not skills:
        await callback.answer("Сначала добавь навык через /start", show_alert=True)
        return

    first = skills[0]
    text = (
        "☀️ Отлично! Начнём прямо сейчас.\n\n"
        f"📌 {first['name']}:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=step_type_keyboard(first["id"])
    )
    await state.update_data(morning_chosen={})
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