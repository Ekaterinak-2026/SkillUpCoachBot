"""
Обработчик команды /start и онбординг.
Здесь пользователь знакомится с ботом, выбирает навык и настраивает время.
"""

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import (
    skills_keyboard,
    time_setup_keyboard,
    start_choice_keyboard,
    timezone_keyboard,
    add_more_skills_keyboard,
)
from database import (
    add_user,
    get_user,
    update_user_skill,
    update_user_time,
    update_user_timezone,
    add_skill,
    get_active_skills,
    count_active_skills,
    MAX_SKILLS,
)
import texts

# Роутер для этого файла
router = Router()


# ============ СОСТОЯНИЯ (FSM) ============

class Onboarding(StatesGroup):
    choosing_skill = State()
    entering_custom_skill = State()
    adding_more_skills = State()
    choosing_timezone = State()
    setting_morning = State()
    setting_evening = State()
# ============ /start ============

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработка команды /start."""
    user_id = message.from_user.id
    username = message.from_user.first_name or "друг"

    # Сохраняем пользователя в БД (если его ещё нет)
    await add_user(user_id, username)

    # Проверяем, есть ли уже навык
    user = await get_user(user_id)
    if user and user.get("skill"):
        # Пользователь уже настроен
        await message.answer(
            texts.ALREADY_REGISTERED + "\n\n" +
            texts.STATS.format(
                name=username,
                skill=user["skill"],
                streak=user["streak"],
                best_streak=user["best_streak"],
                total=user["total_success"],
                week_done=0,  # позже посчитаем точно
            )
        )
        return

    # Новый пользователь — начинаем онбординг
    await state.set_state(Onboarding.choosing_skill)
    await message.answer(
        texts.WELCOME,
        reply_markup=skills_keyboard()
    )


# ============ ВЫБОР НАВЫКА ============
@router.callback_query(F.data == "onb:add_more", Onboarding.adding_more_skills)
async def process_add_more(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь хочет добавить ещё навык."""
    user_id = callback.from_user.id
    count = await count_active_skills(user_id)

    if count >= MAX_SKILLS:
        await callback.answer("Достигнут максимум навыков", show_alert=True)
        return

    await callback.message.edit_text(
        "Какой навык хочешь добавить ещё?",
        reply_markup=skills_keyboard()
    )
    await state.set_state(Onboarding.choosing_skill)
    await callback.answer()


@router.callback_query(F.data == "onb:done", Onboarding.adding_more_skills)
async def process_done_adding(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь закончил добавлять навыки — переходим к часовому поясу."""
    user_id = callback.from_user.id
    skills = await get_active_skills(user_id)

    if not skills:
        await callback.answer("Сначала выбери хотя бы один навык", show_alert=True)
        return

    await callback.message.edit_text(
        texts.CHOOSE_TIMEZONE,
        reply_markup=timezone_keyboard()
    )
    await state.set_state(Onboarding.choosing_timezone)
    await callback.answer()


@router.callback_query(F.data.startswith("tz:"), Onboarding.choosing_timezone)
async def process_timezone_choice(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь выбрал часовой пояс."""
    tz_name = callback.data.split(":", 1)[1]

    # Красивое название для сообщения
    tz_labels = {
        "Europe/Kaliningrad": "Калининград (UTC+2)",
        "Europe/Moscow": "Москва (UTC+3)",
        "Europe/Samara": "Самара (UTC+4)",
        "Asia/Yekaterinburg": "Екатеринбург (UTC+5)",
        "Asia/Omsk": "Омск (UTC+6)",
        "Asia/Novosibirsk": "Новосибирск (UTC+7)",
        "Asia/Irkutsk": "Иркутск (UTC+8)",
        "Asia/Yakutsk": "Якутск (UTC+9)",
        "Asia/Vladivostok": "Владивосток (UTC+10)",
        "Asia/Magadan": "Магадан (UTC+11)",
        "Asia/Kamchatka": "Камчатка (UTC+12)",
    }
    tz_label = tz_labels.get(tz_name, tz_name)

    await state.update_data(timezone=tz_name)
    await callback.message.edit_text(
        texts.TIMEZONE_SAVED.format(timezone_name=tz_label) + "\n\n" + texts.SET_TIME_PROMPT,
        reply_markup=time_setup_keyboard()
    )
    # НЕ меняем состояние — оставляем choosing_timezone, чтобы
    # пользователь мог нажать «Оставить по умолчанию» или «Настроить»
    await callback.answer()

@router.callback_query(F.data.startswith("skill:"), Onboarding.choosing_skill)
async def process_skill_choice(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь выбрал навык из списка — сохраняем и предлагаем добавить ещё."""
    skill = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    if skill == "other":
        await callback.message.edit_text(texts.CHOOSE_SKILL_OTHER)
        await state.set_state(Onboarding.entering_custom_skill)
        await callback.answer()
        return

    # Пытаемся добавить навык в БД
    result = await add_skill(user_id, skill)

    if result == -2:  # дубликат
        await callback.message.edit_text(
            texts.SKILL_ALREADY_EXISTS,
            reply_markup=add_more_skills_keyboard(
                await count_active_skills(user_id), MAX_SKILLS
            )
        )
        await callback.answer()
        return

    if result == -1:  # достигнут лимит
        await callback.message.edit_text(
            texts.MAX_SKILLS_REACHED,
            reply_markup=add_more_skills_keyboard(MAX_SKILLS, MAX_SKILLS)
        )
        await callback.answer()
        return

    # Успех — показываем «Хочешь ещё?»
    skills = await get_active_skills(user_id)
    skills_list = ", ".join([s["name"] for s in skills])

    await callback.message.edit_text(
        texts.SKILL_ADDED.format(skill=skill, skills_list=skills_list),
        reply_markup=add_more_skills_keyboard(len(skills), MAX_SKILLS)
    )
    await state.set_state(Onboarding.adding_more_skills)
    await callback.answer()

@router.message(Onboarding.entering_custom_skill, ~F.text.startswith("/"))
async def process_custom_skill(message: Message, state: FSMContext) -> None:
    """Пользователь ввёл свой навык текстом."""
    skill = message.text.strip()[:50]
    user_id = message.from_user.id

    if not skill:
        await message.answer("Напиши название навыка.")
        return

    result = await add_skill(user_id, skill)

    if result == -2:
        await message.answer(
            texts.SKILL_ALREADY_EXISTS,
            reply_markup=add_more_skills_keyboard(
                await count_active_skills(user_id), MAX_SKILLS
            )
        )
        return

    if result == -1:
        await message.answer(
            texts.MAX_SKILLS_REACHED,
            reply_markup=add_more_skills_keyboard(MAX_SKILLS, MAX_SKILLS)
        )
        return

    skills = await get_active_skills(user_id)
    skills_list = ", ".join([s["name"] for s in skills])

    await message.answer(
        texts.SKILL_ADDED.format(skill=skill, skills_list=skills_list),
        reply_markup=add_more_skills_keyboard(len(skills), MAX_SKILLS)
    )
    await state.set_state(Onboarding.adding_more_skills)


# ============ НАСТРОЙКА ВРЕМЕНИ ============

@router.callback_query(F.data == "time:default", Onboarding.choosing_timezone)
async def process_default_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Оставляем время по умолчанию: 9:00 и 20:00."""
    data = await state.get_data()
    timezone = data.get("timezone", "Europe/Moscow")

    user_id = callback.from_user.id
    skills = await get_active_skills(user_id)
    if skills:
        await update_user_skill(user_id, skills[0]["name"])
    await update_user_timezone(user_id, timezone)
    await update_user_time(user_id, morning="09:00", evening="20:00")

    await callback.message.edit_text(
        texts.ONBOARDING_DONE.format(morning_time="09:00")
    )
    await callback.message.answer(
        texts.START_CHOICE,
        reply_markup=start_choice_keyboard("09:00", timezone)
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "time:custom", Onboarding.choosing_timezone)
async def process_custom_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь хочет настроить своё время."""
    await callback.message.edit_text(texts.ASK_MORNING_TIME)
    await state.set_state(Onboarding.setting_morning)
    await callback.answer()


@router.message(Onboarding.setting_morning, ~F.text.startswith("/"))
async def process_morning_time(message: Message, state: FSMContext) -> None:
    """Получаем утреннее время."""
    time_str = message.text.strip()

    if not _is_valid_time(time_str):
        await message.answer(texts.INVALID_TIME)
        return

    await state.update_data(morning_time=time_str)
    await message.answer(texts.ASK_EVENING_TIME)
    await state.set_state(Onboarding.setting_evening)


@router.message(Onboarding.setting_evening, ~F.text.startswith("/"))
async def process_evening_time(message: Message, state: FSMContext) -> None:
    """Получаем вечернее время и завершаем онбординг."""
    time_str = message.text.strip()

    if not _is_valid_time(time_str):
        await message.answer(texts.INVALID_TIME)
        return

    data = await state.get_data()
    morning = data.get("morning_time")
    timezone = data.get("timezone", "Europe/Moscow")

    user_id = message.from_user.id
    skills = await get_active_skills(user_id)
    if skills:
        await update_user_skill(user_id, skills[0]["name"])
    await update_user_timezone(user_id, timezone)
    await update_user_time(user_id, morning=morning, evening=time_str)
    await message.answer(
        texts.ONBOARDING_DONE.format(morning_time=morning)
    )
    await message.answer(
        texts.START_CHOICE,
        reply_markup=start_choice_keyboard(morning, timezone)
    )
    await state.clear()
  


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


    

    