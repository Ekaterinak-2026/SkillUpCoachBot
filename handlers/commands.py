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
    get_active_skills,
    get_archived_skills,
    get_skill_by_id,
    count_active_skills,
    add_skill,
    archive_skill,
    restore_skill,
    MAX_SKILLS,
)
from keyboards import (
    settings_keyboard,
    skills_keyboard,
    change_skill_confirm_keyboard,
    reset_confirm_keyboard,
    skills_menu_keyboard,
    skills_add_keyboard,
    archive_choose_keyboard,
    restore_choose_keyboard,
    archive_confirm_keyboard,
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
class SkillsStates(StatesGroup):
    """Состояния для команды /skills."""
    adding_custom = State()


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
    # ============ КОМАНДА /skills ============

def _build_skills_text(skills: list[dict], archived: list[dict]) -> str:
    """Формирует текст меню навыков."""
    lines = [texts.SKILLS_MENU_TITLE.format(count=len(skills)), ""]

    if skills:
        for s in skills:
            lines.append(f"• {s['name']}")
    else:
        lines.append(texts.SKILLS_MENU_NO_ACTIVE)

    if archived:
        lines.append("")
        lines.append(texts.SKILLS_MENU_ARCHIVED_NOTE.format(count=len(archived)))

    lines.append("")
    lines.append(texts.SKILLS_MENU_PROMPT)
    return "\n".join(lines)


async def _show_skills_menu(message: Message, user_id: int, edit: bool = False) -> None:
    """Показывает или обновляет меню /skills."""
    skills = await get_active_skills(user_id)
    archived = await get_archived_skills(user_id)

    text = _build_skills_text(skills, archived)
    keyboard = skills_menu_keyboard(bool(skills), bool(archived))

    if edit:
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.message(Command("skills"))
async def cmd_skills(message: Message, state: FSMContext) -> None:
    """Открывает меню управления навыками."""
    await state.clear()
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user or not user.get("skill"):
        await message.answer(texts.NOT_REGISTERED)
        return

    await _show_skills_menu(message, user_id, edit=False)


@router.callback_query(F.data == "skills:menu")
async def cb_skills_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в главное меню /skills."""
    await state.clear()
    await _show_skills_menu(callback.message, callback.from_user.id, edit=True)
    await callback.answer()


@router.callback_query(F.data == "skills:close")
async def cb_skills_close(callback: CallbackQuery, state: FSMContext) -> None:
    """Закрывает меню /skills."""
    await state.clear()
    await callback.message.edit_text("Ок, меню закрыто.")
    await callback.answer()


# ----- ДОБАВЛЕНИЕ -----

@router.callback_query(F.data == "skills:add")
async def cb_skills_add(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает список навыков для добавления."""
    user_id = callback.from_user.id
    count = await count_active_skills(user_id)

    if count >= MAX_SKILLS:
        await callback.answer(texts.MAX_SKILLS_ALERT, show_alert=True)
        return

    await callback.message.edit_text(
        "➕ Какой навык хочешь добавить?",
        reply_markup=skills_add_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("skill_add:"))
async def cb_skill_add_choose(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь выбрал навык для добавления."""
    skill = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    if skill == "other":
        await callback.message.edit_text(
            "✍️ Напиши название навыка:"
        )
        await state.set_state(SkillsStates.adding_custom)
        await callback.answer()
        return

    result = await add_skill(user_id, skill)

    if result == -1:
        await callback.answer(texts.MAX_SKILLS_ALERT, show_alert=True)
        return
    if result == -2:
        await callback.answer(texts.SKILL_DUPLICATE_ALERT, show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        texts.SKILL_ADDED_FROM_MENU.format(skill=skill)
    )
    await _show_skills_menu(callback.message, user_id, edit=False)
    await callback.answer()


@router.message(SkillsStates.adding_custom, ~F.text.startswith("/"))
async def cb_skill_add_custom(message: Message, state: FSMContext) -> None:
    """Пользователь ввёл свой навык текстом."""
    skill = message.text.strip()[:50]
    user_id = message.from_user.id

    if not skill:
        await message.answer("Напиши название навыка.")
        return

    result = await add_skill(user_id, skill)

    if result == -1:
        await message.answer(texts.MAX_SKILLS_ALERT)
        await state.clear()
        return
    if result == -2:
        await message.answer(texts.SKILL_DUPLICATE_ALERT)
        await state.clear()
        return

    await state.clear()
    await message.answer(texts.SKILL_ADDED_FROM_MENU.format(skill=skill))
    await _show_skills_menu(message, user_id, edit=False)


# ----- УДАЛЕНИЕ (АРХИВАЦИЯ) -----

@router.callback_query(F.data == "skills:delete")
async def cb_skills_delete(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает список навыков для архивации."""
    user_id = callback.from_user.id
    skills = await get_active_skills(user_id)

    if not skills:
        await callback.answer("Нечего удалять.", show_alert=True)
        return

    await callback.message.edit_text(
        texts.CHOOSE_SKILL_TO_ARCHIVE,
        reply_markup=archive_choose_keyboard(skills)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("skill_arch:"))
async def cb_skill_arch(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь выбрал навык для архивации — просим подтверждение."""
    try:
        skill_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer()
        return

    skill = await get_skill_by_id(skill_id)
    if not skill or skill["user_id"] != callback.from_user.id:
        await callback.answer("Навык не найден", show_alert=True)
        return

    await callback.message.edit_text(
        texts.ARCHIVE_CONFIRM.format(skill=skill["name"]),
        reply_markup=archive_confirm_keyboard(skill_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("skill_arch_yes:"))
async def cb_skill_arch_yes(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение архивации."""
    try:
        skill_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer()
        return

    skill = await get_skill_by_id(skill_id)
    if not skill or skill["user_id"] != callback.from_user.id:
        await callback.answer("Навык не найден", show_alert=True)
        return

    await archive_skill(skill_id)
    user_id = callback.from_user.id

    # Если у пользователя не осталось активных — обновляем users.skill
    remaining = await get_active_skills(user_id)
    if remaining:
        await update_user_skill(user_id, remaining[0]["name"])

    await callback.message.edit_text(texts.SKILL_ARCHIVED_OK.format(skill=skill["name"]))
    await _show_skills_menu(callback.message, user_id, edit=False)
    await callback.answer()


# ----- ВОССТАНОВЛЕНИЕ -----

@router.callback_query(F.data == "skills:restore")
async def cb_skills_restore(callback: CallbackQuery, state: FSMContext) -> None:
    """Показывает список архивных навыков."""
    user_id = callback.from_user.id
    archived = await get_archived_skills(user_id)

    if not archived:
        await callback.answer(texts.NO_ARCHIVED_SKILLS, show_alert=True)
        return

    # Проверка лимита
    active_count = await count_active_skills(user_id)
    if active_count >= MAX_SKILLS:
        await callback.answer(texts.MAX_SKILLS_ALERT, show_alert=True)
        return

    await callback.message.edit_text(
        texts.CHOOSE_SKILL_TO_RESTORE,
        reply_markup=restore_choose_keyboard(archived)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("skill_restore:"))
async def cb_skill_restore(callback: CallbackQuery, state: FSMContext) -> None:
    """Восстанавливает выбранный навык."""
    try:
        skill_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer()
        return

    skill = await get_skill_by_id(skill_id)
    if not skill or skill["user_id"] != callback.from_user.id:
        await callback.answer("Навык не найден", show_alert=True)
        return

    await restore_skill(skill_id)
    user_id = callback.from_user.id

    await callback.message.edit_text(texts.SKILL_RESTORED_OK.format(skill=skill["name"]))
    await _show_skills_menu(callback.message, user_id, edit=False)
    await callback.answer()