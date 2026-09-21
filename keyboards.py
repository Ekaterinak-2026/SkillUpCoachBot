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

def step_type_keyboard(skill_id: int) -> InlineKeyboardMarkup:
    """Кнопки выбора типа шага утром (с привязкой к skill_id)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Теория", callback_data=f"ms:{skill_id}:теория")
    builder.button(text="💻 Практика", callback_data=f"ms:{skill_id}:практика")
    builder.button(text="🗣 Общение", callback_data=f"ms:{skill_id}:общение")
    builder.button(text="🧠 Рефлексия", callback_data=f"ms:{skill_id}:рефлексия")
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
def start_choice_keyboard(morning_time: str, timezone_name: str = "Europe/Moscow") -> InlineKeyboardMarkup:
    """Кнопки выбора: начать сейчас / сегодня / завтра.
    Кнопка «Сегодня» показывается только если morning_time ещё не прошло."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = ZoneInfo("Europe/Moscow")

    now_hm = datetime.now(tz).strftime("%H:%M")

    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Начать сейчас", callback_data="start:now")
    if morning_time > now_hm:
        builder.button(text=f"📅 Сегодня в {morning_time}", callback_data="start:today")
    builder.button(text=f"📅 Завтра в {morning_time}", callback_data="start:tomorrow")
    builder.adjust(1)
    return builder.as_markup()
def timezone_keyboard() -> InlineKeyboardMarkup:
    """Кнопки выбора часового пояса."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Калининград (UTC+2)", callback_data="tz:Europe/Kaliningrad")
    builder.button(text="Москва (UTC+3)", callback_data="tz:Europe/Moscow")
    builder.button(text="Самара (UTC+4)", callback_data="tz:Europe/Samara")
    builder.button(text="Екатеринбург (UTC+5)", callback_data="tz:Asia/Yekaterinburg")
    builder.button(text="Омск (UTC+6)", callback_data="tz:Asia/Omsk")
    builder.button(text="Новосибирск (UTC+7)", callback_data="tz:Asia/Novosibirsk")
    builder.button(text="Иркутск (UTC+8)", callback_data="tz:Asia/Irkutsk")
    builder.button(text="Якутск (UTC+9)", callback_data="tz:Asia/Yakutsk")
    builder.button(text="Владивосток (UTC+10)", callback_data="tz:Asia/Vladivostok")
    builder.button(text="Магадан (UTC+11)", callback_data="tz:Asia/Magadan")
    builder.button(text="Камчатка (UTC+12)", callback_data="tz:Asia/Kamchatka")
    builder.adjust(2)
    return builder.as_markup()
def reset_confirm_keyboard() -> InlineKeyboardMarkup:
    """Кнопки подтверждения сброса профиля."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚠️ Да, сбросить", callback_data="reset:yes")
    builder.button(text="❌ Отмена", callback_data="reset:no")
    builder.adjust(1)
    return builder.as_markup()
def nudge_keyboard() -> InlineKeyboardMarkup:
    """Кнопка CTA для nudge-сообщений."""
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Сделать шаг сейчас", callback_data="start:now")
    builder.adjust(1)
    return builder.as_markup()
def add_more_skills_keyboard(has_skills: int, max_skills: int = 5) -> InlineKeyboardMarkup:
    """Кнопки после выбора навыка: добавить ещё или готово."""
    builder = InlineKeyboardBuilder()
    if has_skills < max_skills:
        builder.button(text="➕ Добавить ещё навык", callback_data="onb:add_more")
    builder.button(text="✅ Готово, продолжить", callback_data="onb:done")
    builder.adjust(1)
    return builder.as_markup()
# ============ УПРАВЛЕНИЕ НАВЫКАМИ ============

def skills_menu_keyboard(has_active: bool, has_archived: bool) -> InlineKeyboardMarkup:
    """Главное меню /skills."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить навык", callback_data="skills:add")
    if has_active:
        builder.button(text="🗑 Удалить навык", callback_data="skills:delete")
    if has_archived:
        builder.button(text="♻️ Восстановить из архива", callback_data="skills:restore")
    builder.button(text="❌ Закрыть", callback_data="skills:close")
    builder.adjust(1)
    return builder.as_markup()


def skills_add_keyboard() -> InlineKeyboardMarkup:
    """Список навыков для добавления из /skills (отдельные callback_data)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Python", callback_data="skill_add:Python")
    builder.button(text="Java", callback_data="skill_add:Java")
    builder.button(text="SQL", callback_data="skill_add:SQL")
    builder.button(text="Английский", callback_data="skill_add:Английский")
    builder.button(text="System Design", callback_data="skill_add:System Design")
    builder.button(text="Другое", callback_data="skill_add:other")
    builder.button(text="← Назад", callback_data="skills:menu")
    builder.adjust(2)
    return builder.as_markup()


def archive_choose_keyboard(skills: list[dict]) -> InlineKeyboardMarkup:
    """Кнопки выбора навыка для архивации."""
    builder = InlineKeyboardBuilder()
    for s in skills:
        builder.button(text=f"🗑 {s['name']}", callback_data=f"skill_arch:{s['id']}")
    builder.button(text="← Назад", callback_data="skills:menu")
    builder.adjust(1)
    return builder.as_markup()


def restore_choose_keyboard(skills: list[dict]) -> InlineKeyboardMarkup:
    """Кнопки выбора навыка для восстановления."""
    builder = InlineKeyboardBuilder()
    for s in skills:
        builder.button(text=f"♻️ {s['name']}", callback_data=f"skill_restore:{s['id']}")
    builder.button(text="← Назад", callback_data="skills:menu")
    builder.adjust(1)
    return builder.as_markup()


def archive_confirm_keyboard(skill_id: int) -> InlineKeyboardMarkup:
    """Подтверждение архивации навыка."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, в архив", callback_data=f"skill_arch_yes:{skill_id}")
    builder.button(text="❌ Отмена", callback_data="skills:menu")
    builder.adjust(1)
    return builder.as_markup()