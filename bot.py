"""
Вебинарный бот — регистрация через подписку на канал
Aiogram v3 + SQLite + APScheduler
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ============================================================
#  НАСТРОЙКИ — заполни перед запуском
# ============================================================
BOT_TOKEN        = "8740029080:AAF1v_T-uA4NkyEkULJh3zdSvGaZJ8dgC-s"
CHANNEL_ID       = "@tellusell"           # username или -100123456789
CHANNEL_LINK     = "https://t.me/твой_канал"

WEBINAR_NAME     = "Я один думаю, что в трейдинг лучше не лезть?"
WEBINAR_TOPIC    = "этой теме"             # для вопроса про уровень
WEBINAR_DATE_STR = "30 апреля в 19:00 "
WEBINAR_LINK     = "https://ссылка-на-трансляцию.com"

# Дата и время вебинара (для планировщика напоминаний)
WEBINAR_DATETIME = datetime(2026, 4, 30, 19, 0)   # год, месяц, день, час, мин

# file_id чек-листа — получи, отправив файл боту @userinfobot или своему боту
CHECKLIST_FILE_ID = "BQACAgIAAxkBAAI..."   # TODO: вставь реальный file_id

ADMIN_ID = 396728532                       # Твой Telegram ID для уведомлений о заявках
# ============================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


# ─── База данных ──────────────────────────────────────────────────────────────

def init_db():
    with sqlite3.connect("users.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER PRIMARY KEY,
                username     TEXT,
                full_name    TEXT,
                name         TEXT,
                contact      TEXT,
                level        TEXT,
                registered_at TEXT
            )
        """)

def save_user(user_id, username, full_name, name, contact, level):
    with sqlite3.connect("users.db") as conn:
        conn.execute("""
            INSERT OR REPLACE INTO users
              (user_id, username, full_name, name, contact, level, registered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, full_name, name, contact, level,
              datetime.now().strftime("%Y-%m-%d %H:%M")))

def get_all_users() -> list[int]:
    with sqlite3.connect("users.db") as conn:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
    return [r[0] for r in rows]


# ─── FSM-состояния ────────────────────────────────────────────────────────────

class Form(StatesGroup):
    waiting_name    = State()
    waiting_contact = State()
    waiting_level   = State()


# ─── Клавиатуры ───────────────────────────────────────────────────────────────

def kb_start() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Перейти в канал",  url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Я подписался",     callback_data="check_sub")],
    ])

def kb_level() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌱 Новичок", callback_data="level_beginner"),
        InlineKeyboardButton(text="🚀 Профи",   callback_data="level_pro"),
    ]])


# ─── Шаг 1: /start ────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Привет! 🚀\n\n"
        f"Ты в одном шаге от регистрации на вебинар <b>«{WEBINAR_NAME}»</b>.\n\n"
        f"Чтобы заявка была принята, а я смог отправить тебе ссылку на трансляцию — "
        f"подпишись на наш закрытый канал. Там уже лежит первый видео-урок, "
        f"который стоит посмотреть до начала.\n\n"
        f"1. Подпишись на канал ниже\n"
        f"2. Нажми кнопку <b>«✅ Я подписался»</b> 👇",
        reply_markup=kb_start(),
        parse_mode="HTML",
    )


# ─── Шаг 2: Проверка подписки ─────────────────────────────────────────────────

@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        subscribed = member.status not in ("left", "kicked", "banned")
    except Exception as e:
        logging.warning(f"get_chat_member error: {e}")
        subscribed = False

    if not subscribed:
        await callback.answer("Подписка не найдена 👀", show_alert=True)
        await callback.message.edit_text(
            "Ой, кажется, подписка ещё не оформлена 😊\n\n"
            "Пожалуйста, подпишись на канал — это единственное условие "
            "для участия в вебинаре и получения бонуса.",
            reply_markup=kb_start(),
        )
        return

    # ─── Шаг 3: Выдача бонуса и сбор данных ──────────────────────────────────
    await callback.answer()
    await callback.message.delete()

    # Отправляем чек-лист (замени на send_message, если нет файла)
    try:
        await bot.send_document(
            chat_id=user_id,
            document=CHECKLIST_FILE_ID,
            caption=(
                "🎉 Супер, ты в деле!\n\n"
                "Лови обещанный чек-лист. "
                "Изучи его до вебинара — будет намного больше пользы от эфира."
            ),
        )
    except Exception:
        # Если file_id ещё не настроен — просто текст
        await bot.send_message(
            user_id,
            "🎉 Супер, ты в деле! Чек-лист скоро пришлём отдельно."
        )

    await bot.send_message(user_id, "Как мне к тебе обращаться? ✍️")
    await state.set_state(Form.waiting_name)


# ─── Анкета: имя ──────────────────────────────────────────────────────────────

@dp.message(Form.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer(
        f"Отлично, {message.text.strip()}! 👋\n\n"
        "Оставь телефон или email — напомним о старте за час до эфира 📲"
    )
    await state.set_state(Form.waiting_contact)


# ─── Анкета: контакт ──────────────────────────────────────────────────────────

@dp.message(Form.waiting_contact)
async def process_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text.strip())
    await message.answer(
        f"Последний вопрос 😊\n\nКакой у тебя уровень в {WEBINAR_TOPIC}?",
        reply_markup=kb_level(),
    )
    await state.set_state(Form.waiting_level)


# ─── Анкета: уровень → финал ──────────────────────────────────────────────────

@dp.callback_query(F.data.startswith("level_"))
async def process_level(callback: CallbackQuery, state: FSMContext):
    level = "Новичок" if callback.data == "level_beginner" else "Профи"
    data  = await state.get_data()
    user  = callback.from_user

    save_user(
        user_id   = user.id,
        username  = user.username or "",
        full_name = user.full_name or "",
        name      = data.get("name", ""),
        contact   = data.get("contact", ""),
        level     = level,
    )
    await state.clear()

    # Шаг 4: подтверждение
    await callback.message.edit_text(
        f"✅ <b>Заявка принята!</b>\n\n"
        f"Запиши в календарь: <b>{WEBINAR_DATE_STR}</b>\n"
        f"Ссылка на трансляцию придёт сюда — за час до старта.\n\n"
        f"До встречи на вебинаре! 🔥",
        parse_mode="HTML",
    )

    # Уведомление администратору
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🆕 <b>Новая заявка!</b>\n"
            f"👤 {data.get('name')} (@{user.username})\n"
            f"📞 {data.get('contact')}\n"
            f"📊 Уровень: {level}",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ─── Рассылки (догрев) ────────────────────────────────────────────────────────

async def broadcast(text: str):
    """Рассылка всем зарегистрированным пользователям."""
    sent, failed = 0, 0
    for uid in get_all_users():
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)   # Защита от флуда
        except Exception:
            failed += 1
    logging.info(f"Рассылка: {sent} доставлено, {failed} ошибок")


async def reminder_24h():
    await broadcast(
        f"⏰ <b>Напоминание — до вебинара меньше суток!</b>\n\n"
        f"Завтра в <b>{WEBINAR_DATE_STR}</b> встречаемся на вебинаре "
        f"«{WEBINAR_NAME}».\n\n"
        f"На эфире разберём:\n"
        f"— [пункт 1]\n"
        f"— [пункт 2]\n"
        f"— [пункт 3]\n\n"
        f"Готовь вопросы заранее — отвечу в прямом эфире 💬"
    )


async def reminder_1h():
    await broadcast(
        f"🔔 <b>Начинаем через час!</b>\n\n"
        f"Вебинар «{WEBINAR_NAME}» стартует уже скоро.\n\n"
        f"Готовь блокнот — будет плотно и по делу 🚀\n"
        f"Ссылка придёт сюда в момент старта."
    )


async def reminder_start():
    await broadcast(
        f"🔴 <b>Мы в эфире!</b>\n\n"
        f"Заходи прямо сейчас: {WEBINAR_LINK}"
    )


# ─── Планировщик ──────────────────────────────────────────────────────────────

def setup_scheduler():
    scheduler.add_job(
        reminder_24h,
        trigger="date",
        run_date=WEBINAR_DATETIME - timedelta(hours=24),
        id="reminder_24h",
    )
    scheduler.add_job(
        reminder_1h,
        trigger="date",
        run_date=WEBINAR_DATETIME - timedelta(hours=1),
        id="reminder_1h",
    )
    scheduler.add_job(
        reminder_start,
        trigger="date",
        run_date=WEBINAR_DATETIME,
        id="reminder_start",
    )
    logging.info(
        f"Рассылки запланированы: "
        f"-24ч / -1ч / старт {WEBINAR_DATETIME.strftime('%d.%m.%Y %H:%M')}"
    )


# ─── Запуск ───────────────────────────────────────────────────────────────────

async def main():
    init_db()
    setup_scheduler()
    scheduler.start()
    logging.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
