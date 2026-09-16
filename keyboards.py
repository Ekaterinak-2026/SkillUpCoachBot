"""
Все клавиатуры (кнопки) бота SkillUp Coach.
Используем InlineKeyboardMarkup из aiogram 3.x.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ============ ОНБОРДИНГ ============

def skills_keyboard() -> InlineKeyboardMarkup:
    """Кнопки выбора навыка на старте."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Python", callback_data="skill:Python")
    builder.button(text="Java", callback_data="skill:Java")
    builder.button(text="SQL", callback_data="skill:SQL")
    builder.button(text="Английский", callback_data="skill:Английский")
    builder.button(text="System Design", callback_data="skill:System Design")
    builder.button(text="Другое", callback_data="skill:other")
    builder.adjust(2)  # по 2 кнопки в ряд
    return builder.as_markup()


def time_setup_keyboard() -> InlineKeyboardMarkup:
    """Кнопки настройки времени уведомлений."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Оставить 9:00 и 20:00", callback_data="time:default")
    builder.button(text="Настроить своё время", callback_data="time:custom")
    builder.adjust(1)
    return builder.as_markup()


# ============ УТРЕННИЙ ВОПРОС ============

def step_type_keyboard() -> InlineKeyboardMarkup:
    """Кнопки выбора типа шага утром."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Теория", callback_data="step:теория")
    builder.button(text="💻 Практика", callback_data="step:практика")
    builder.button(text="🗣 Общение", callback_data="step:общение")
    builder.button(text="🧠 Рефлексия", callback_data="step:рефлексия")
    builder.adjust(2)
    return builder.as_markup()


# ============ ВЕЧЕРНИЙ ЧЕКАП ============

def evening_check_keyboard() -> InlineKeyboardMarkup:
    """Кнопки ответа на вечерний вопрос (если план был)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, сделал", callback_data="evening:done")
    builder.button(text="❌ Нет, не успел", callback_data="evening:failed")
    builder.button(text="⏳ Перенесу на завтра", callback_data="evening:postponed")
    builder.adjust(1)
    return builder.as_markup()


def evening_no_plan_keyboard() -> InlineKeyboardMarkup:
    """Кнопки, если утром пользователь не выбрал шаг."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Сделаю сейчас", callback_data="noplan:now")
    builder.button(text="⏳ Перенесу на завтра", callback_data="noplan:postponed")
    builder.button(text="❌ Пропущу", callback_data="noplan:skip")
    builder.adjust(1)
    return builder.as_markup()


# ============ КОМАНДА /settings ============

def settings_keyboard() -> InlineKeyboardMarkup:
    """Кнопки меню настроек."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Изменить время", callback_data="settings:time")
    builder.button(text="Сменить навык", callback_data="settings:skill")
    builder.button(text="Назад", callback_data="settings:back")
    builder.adjust(1)
    return builder.as_markup()


def change_skill_confirm_keyboard() -> InlineKeyboardMarkup:
    """Кнопки подтверждения смены навыка."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, сменить", callback_data="changeskill:yes")
    builder.button(text="❌ Отмена", callback_data="changeskill:no")
    builder.adjust(1)
    return builder.as_markup()