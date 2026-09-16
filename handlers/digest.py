"""
Обработчик команды /digest.
Отправляет недельный дайджест вручную — удобно для тестирования
и для тех, кто хочет посмотреть статистику до воскресенья.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import get_user, get_week_stats
import texts

router = Router()


@router.message(Command("digest"))
async def cmd_digest(message: Message) -> None:
    """Отправляет пользователю дайджест по запросу."""
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user or not user.get("skill"):
        await message.answer(texts.NOT_REGISTERED)
        return

    stats = await get_week_stats(user_id)

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

    # Совет
    if user["best_streak"] >= 5:
        text += texts.DIGEST_TIP_LONG_STREAK.format(streak=user["best_streak"])
    elif stats["done_count"] < 3:
        text += texts.DIGEST_TIP_MANY_MISSES
    else:
        text += texts.DIGEST_TIP_DEFAULT

    await message.answer(text)