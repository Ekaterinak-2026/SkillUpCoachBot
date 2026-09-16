# Схема базы данных SkillUp Coach

## Таблица `users`
Хранит профиль пользователя и текущий прогресс.

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| user_id | INTEGER PRIMARY KEY | Telegram ID пользователя |
| username | TEXT | Имя пользователя (для обращений) |
| skill | TEXT | Выбранный навык (например, «Python») |
| morning_time | TEXT | Время утреннего вопроса (ЧЧ:ММ) |
| evening_time | TEXT | Время вечернего чекапа (ЧЧ:ММ) |
| streak | INTEGER | Текущая серия дней |
| best_streak | INTEGER | Лучшая серия за всё время |
| total_success | INTEGER | Всего выполненных шагов |
| created_at | TIMESTAMP | Дата регистрации |

## Таблица `daily_steps`
Хранит ежедневные шаги: план утром, отметка вечером.

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| id | INTEGER PRIMARY KEY AUTOINCREMENT | ID записи |
| user_id | INTEGER | Ссылка на users.user_id |
| date | TEXT | Дата (YYYY-MM-DD) |
| step_type | TEXT | теория / практика / общение / рефлексия |
| status | TEXT | запланирован / выполнен / пропущен / перенесён |
| created_at | TIMESTAMP | Когда создана запись |

## Связи
- `daily_steps.user_id` → `users.user_id` (один ко многим).

## Примеры запросов
- Получить текущую серию: `SELECT streak FROM users WHERE user_id = ?`
- Получить шаги за неделю: `SELECT * FROM daily_steps WHERE user_id = ? AND date >= ?`
- Отметить выполнение: `UPDATE daily_steps SET status = 'выполнен' WHERE id = ?`