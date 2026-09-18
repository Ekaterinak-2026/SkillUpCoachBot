"""
Обработчики команд: /stats, /settings, /help.
Плюс логика смены навыка и времени через настройки.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    get_user,
    get_week_stats,
    update_user_skill,
    update_user_time,
    reset_user,
)
from keyboards import (
    settings_keyboard,
    skills_keyboard,
    change_skill_confirm_keyboard,
    reset_confirm_keyboard,
)
import texts

router = Router()


# ============ СОСТОЯНИЯ ============

class SettingsStates(StatesGroup):
    """Состояния для команды /settings."""
    menu = State()
    changing_morning = State()
    changing_evening = State()
    changing_skill = State()


# ============ /stats ============

@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Показывает статистику пользователя."""
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user or not user.get("skill"):
        await message.answer(texts.NOT_REGISTERED)
        return

    stats = await get_week_stats(user_id)

    await message.answer(
        texts.STATS.format(
            name=user.get("username") or "друг",
            skill=user["skill"],
            streak=user["streak"],
            best_streak=user["best_streak"],
            total=user["total_success"],
            week_done=stats["done_count"],
        )
    )


# ============ /help ============

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Показывает справку."""
    await message.answer(texts.HELP)


# ============ /settings ============

@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext) -> None:
    """Открывает меню настроек."""
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user or not user.get("skill"):
        await message.answer(texts.NOT_REGISTERED)
        return

    await state.set_state(SettingsStates.menu)
    await message.answer(
        texts.SETTINGS.format(
            skill=user["skill"],
            morning_time=user["morning_time"],
            evening_time=user["evening_time"],
        ),
        reply_markup=settings_keyboard()
    )


# ============ ИЗМЕНЕНИЕ ВРЕМЕНИ ============

@router.callback_query(F.data == "settings:time", SettingsStates.menu)
async def process_change_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь хочет изменить время."""
    await callback.message.edit_text(texts.ASK_MORNING_TIME)
    await state.set_state(SettingsStates.changing_morning)
    await callback.answer()


@router.message(SettingsStates.changing_morning)
async def process_new_morning_time(message: Message, state: FSMContext) -> None:
    """Получаем новое утреннее время."""
    time_str = message.text.strip()

    if not _is_valid_time(time_str):
        await message.answer(texts.INVALID_TIME)
        return

    await update_user_time(message.from_user.id, morning=time_str)
    await message.answer(
        f"🌅 Утреннее время изменено на {time_str}.\n\n"
        f"Теперь напиши новое вечернее время (ЧЧ:ММ):"
    )
    await state.set_state(SettingsStates.changing_evening)


@router.message(SettingsStates.changing_evening)
async def process_new_evening_time(message: Message, state: FSMContext) -> None:
    """Получаем новое вечернее время."""
    time_str = message.text.strip()

    if not _is_valid_time(time_str):
        await message.answer(texts.INVALID_TIME)
        return

    await update_user_time(message.from_user.id, evening=time_str)
    await message.answer(
        f"🌙 Вечернее время изменено на {time_str}. Готово!"
    )
    await state.clear()


# ============ СМЕНА НАВЫКА ============

@router.callback_query(F.data == "settings:skill", SettingsStates.menu)
async def process_change_skill(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь хочет сменить навык — предупреждаем."""
    await callback.message.edit_text(
        texts.CHANGE_SKILL_WARNING,
        reply_markup=change_skill_confirm_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "changeskill:yes", SettingsStates.menu)
async def process_change_skill_yes(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение смены навыка — показываем список."""
    await callback.message.edit_text(
        "Выбери новый навык:",
        reply_markup=skills_keyboard()
    )
    await state.set_state(SettingsStates.changing_skill)
    await callback.answer()


@router.callback_query(F.data == "changeskill:no", SettingsStates.menu)
async def process_change_skill_no(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена смены навыка — возвращаемся в настройки."""
    user = await get_user(callback.from_user.id)
    await callback.message.edit_text(
        texts.SETTINGS.format(
            skill=user["skill"],
            morning_time=user["morning_time"],
            evening_time=user["evening_time"],
        ),
        reply_markup=settings_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("skill:"), SettingsStates.changing_skill)
async def process_new_skill(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь выбрал новый навык."""
    skill = callback.data.split(":", 1)[1]

    if skill == "other":
        await callback.message.edit_text(texts.CHOOSE_SKILL_OTHER)
        # Можно добавить отдельное состояние, но для MVP — упростим
        return

    await update_user_skill(callback.from_user.id, skill)
    await callback.message.edit_text(texts.SKILL_CHANGED.format(skill=skill))
    await state.clear()
    await callback.answer()


# ============ НАЗАД ============

@router.callback_query(F.data == "settings:back", SettingsStates.menu)
async def process_settings_back(callback: CallbackQuery, state: FSMContext) -> None:
    """Закрываем настройки."""
    await callback.message.edit_text("Настройки закрыты.")
    await state.clear()
    await callback.answer()


# ============ ВСПОМОГАТЕЛЬНОЕ ============

def _is_valid_time(time_str: str) -> bool:
    """Проверяет формат ЧЧ:ММ."""
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return False
        hours, minutes = int(parts[0]), int(parts[1])
        return 0 <= hours <= 23 and 0 <= minutes <= 59
    except (ValueError, AttributeError):
        return False
    # ============ /reset ============

@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    """Запрашивает подтверждение сброса профиля."""
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user or not user.get("skill"):
        await message.answer(texts.NOT_REGISTERED)
        return

    await message.answer(
        texts.RESET_CONFIRM,
        reply_markup=reset_confirm_keyboard()
    )


@router.callback_query(F.data == "reset:yes")
async def process_reset_yes(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение сброса."""
    await reset_user(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text(texts.RESET_DONE)
    await callback.answer()


@router.callback_query(F.data == "reset:no")
async def process_reset_no(callback: CallbackQuery) -> None:
    """Отмена сброса."""
    await callback.message.edit_text(texts.RESET_CANCELLED)
    await callback.answer()