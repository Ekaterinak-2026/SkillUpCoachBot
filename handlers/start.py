"""
Обработчик команды /start и онбординг.
Здесь пользователь знакомится с ботом, выбирает навык и настраивает время.
"""

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    add_user,
    get_user,
    update_user_skill,
    update_user_time,
)
from keyboards import (
    skills_keyboard,
    time_setup_keyboard,
    start_choice_keyboard,
)
import texts

# Роутер для этого файла
router = Router()


# ============ СОСТОЯНИЯ (FSM) ============

class Onboarding(StatesGroup):
    """Состояния онбординга — бот помнит, на каком шаге пользователь."""
    choosing_skill = State()       # выбор навыка
    entering_custom_skill = State()  # ввод своего навыка
    setting_morning = State()       # настройка утреннего времени
    setting_evening = State()       # настройка вечернего времени


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

@router.callback_query(F.data.startswith("skill:"), Onboarding.choosing_skill)
async def process_skill_choice(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь выбрал навык из списка."""
    skill = callback.data.split(":", 1)[1]

    if skill == "other":
        # Хотим свой навык
        await callback.message.edit_text(texts.CHOOSE_SKILL_OTHER)
        await state.set_state(Onboarding.entering_custom_skill)
        await callback.answer()
        return

    # Сохраняем навык
    await state.update_data(skill=skill)
    await callback.message.edit_text(
        texts.SKILL_SAVED.format(skill=skill) + "\n\n" + texts.SET_TIME_PROMPT,
        reply_markup=time_setup_keyboard()
    )
    await callback.answer()


@router.message(Onboarding.entering_custom_skill)
async def process_custom_skill(message: Message, state: FSMContext) -> None:
    """Пользователь ввёл свой навык текстом."""
    skill = message.text.strip()[:50]

    if not skill:
        await message.answer("Напиши название навыка.")
        return

    await state.update_data(skill=skill)
    await message.answer(
        texts.SKILL_SAVED.format(skill=skill) + "\n\n" + texts.SET_TIME_PROMPT,
        reply_markup=time_setup_keyboard()
    )
    # ← Добавляем переключение в состояние выбора времени
    await state.set_state(Onboarding.choosing_skill)


# ============ НАСТРОЙКА ВРЕМЕНИ ============

@router.callback_query(F.data == "time:default", Onboarding.choosing_skill)
async def process_default_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Оставляем время по умолчанию: 9:00 и 20:00."""
    data = await state.get_data()
    skill = data.get("skill")

    user_id = callback.from_user.id
    await update_user_skill(user_id, skill)
    await update_user_time(user_id, morning="09:00", evening="20:00")

    await callback.message.edit_text(
        texts.ONBOARDING_DONE.format(morning_time="09:00")
    )
    await callback.message.answer(
        texts.START_CHOICE,
        reply_markup=start_choice_keyboard("09:00")
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "time:custom", Onboarding.choosing_skill)
async def process_custom_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь хочет настроить своё время."""
    await callback.message.edit_text(texts.ASK_MORNING_TIME)
    await state.set_state(Onboarding.setting_morning)
    await callback.answer()


@router.message(Onboarding.setting_morning)
async def process_morning_time(message: Message, state: FSMContext) -> None:
    """Получаем утреннее время."""
    time_str = message.text.strip()

    if not _is_valid_time(time_str):
        await message.answer(texts.INVALID_TIME)
        return

    await state.update_data(morning_time=time_str)
    await message.answer(texts.ASK_EVENING_TIME)
    await state.set_state(Onboarding.setting_evening)


@router.message(Onboarding.setting_evening)
async def process_evening_time(message: Message, state: FSMContext) -> None:
    """Получаем вечернее время и завершаем онбординг."""
    time_str = message.text.strip()

    if not _is_valid_time(time_str):
        await message.answer(texts.INVALID_TIME)
        return

    data = await state.get_data()
    skill = data.get("skill")
    morning = data.get("morning_time")

    user_id = message.from_user.id
    await update_user_skill(user_id, skill)
    await update_user_time(user_id, morning=morning, evening=time_str)

    await message.answer(
        texts.ONBOARDING_DONE.format(morning_time=morning)
    )
  
    await message.answer(
        texts.START_CHOICE,
        reply_markup=start_choice_keyboard(morning)
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