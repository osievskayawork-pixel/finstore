# Вебинарный бот — инструкция по запуску

## Что нужно заполнить в bot.py (блок НАСТРОЙКИ вверху)

| Переменная | Что вставить |
|---|---|
| `BOT_TOKEN` | Токен от @BotFather |
| `CHANNEL_ID` | `@username` канала или `-100xxxxxxxxx` |
| `CHANNEL_LINK` | Прямая ссылка на канал `https://t.me/...` |
| `WEBINAR_NAME` | Название вебинара |
| `WEBINAR_DATE_STR` | Дата и время текстом, например `«25 июля в 19:00»` |
| `WEBINAR_DATETIME` | Дата и время Python-объектом для планировщика |
| `WEBINAR_LINK` | Ссылка на трансляцию (добавишь ближе к дате) |
| `CHECKLIST_FILE_ID` | file_id PDF-чек-листа (см. ниже) |
| `ADMIN_ID` | Твой Telegram ID (узнать у @userinfobot) |

## Как получить file_id чек-листа

1. Запусти бота
2. Отправь ему PDF-файл чек-листа как документ
3. В логах увидишь `document.file_id` — скопируй его

Или добавь временный хэндлер:
```python
@dp.message(F.document)
async def get_file_id(msg: Message):
    await msg.answer(f"file_id: `{msg.document.file_id}`", parse_mode="Markdown")
```

## Важно: права бота в канале

Чтобы `getChatMember` работал, бот должен быть **администратором** в канале
(достаточно минимальных прав).

## Установка и запуск

```bash
pip install -r requirements.txt
python bot.py
```

## Для продакшена (сервер/VPS)

```bash
# Запуск через screen или systemd
screen -S webinar_bot
python bot.py
# Ctrl+A, D — отсоединиться
```

## Структура файлов

```
bot.py           — основной код бота
requirements.txt — зависимости
users.db         — создастся автоматически при первом запуске
```

## Что хранится в базе (users.db)

| Поле | Описание |
|---|---|
| user_id | Telegram ID |
| username | @username |
| full_name | Отображаемое имя в TG |
| name | Имя из анкеты |
| contact | Телефон / email |
| level | Новичок / Профи |
| registered_at | Дата и время регистрации |
