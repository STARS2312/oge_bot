import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import TOKEN, ADMIN_ID
from database import *
from questions import questions
from theory import theory_text
import random
from aiohttp import web

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_sessions = {}

# Старт
@dp.message(Command("start"))
async def start(message: types.Message):
    await add_user(message.from_user.id, message.from_user.username)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Начать тест", callback_data="start_test")],
        [InlineKeyboardButton(text="📖 Теория", callback_data="theory")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ])

    await message.answer("Привет! Готовимся к ОГЭ по истории 📘", reply_markup=kb)


# Начало теста
@dp.callback_query(lambda c: c.data == "start_test")
async def choose_theme(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Империя", callback_data="theme_r_empire")],
        [InlineKeyboardButton(text="⚔ Древняя Русь", callback_data="theme_rus")],
        [InlineKeyboardButton(text="Франция", callback_data="theme_world_france")],
        [InlineKeyboardButton(text="Америка", callback_data="theme_world_america")],
        [InlineKeyboardButton(text="⚔ Древняя Русь", callback_data="theme_rus")],
        [InlineKeyboardButton(text="Австрия", callback_data="theme_austria")]
    ])
    await callback.message.edit_text("Выберите тему:", reply_markup=kb)
    await callback.answer()
async def send_question(user_id):
    session = user_sessions[user_id]
    q = session["questions"][session["current"]]

    buttons = []

    for i, option in enumerate(q["options"]):
        buttons.append(
            [InlineKeyboardButton(
                text=option,
                callback_data=f"answer_{i}"
            )]
        )
@dp.callback_query(lambda c: c.data.startswith("theme_"))
async def start_test(callback: types.CallbackQuery):
    theme = callback.data.split("_")[1]
    theme_questions = questions[theme]

    selected = random.sample(
        theme_questions,
        15 if len(theme_questions) >= 15 else len(theme_questions)
    )
# ----------------- ОТПРАВКА ВОПРОСА -----------------
async def send_question(user_id):
    session = user_sessions[user_id]
    q = session["questions"][session["current"]]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"answer_{i}")]
        for i, opt in enumerate(q["options"])
    ])

    message = await bot.send_message(
        user_id,
        f"📘 Вопрос {session['current']+1}/{len(session['questions'])}\n\n{q['question']}",
        reply_markup=kb
    )

    session["last_message_id"] = message.message_id


# ----------------- ОБРАБОТКА ОТВЕТА -----------------
@dp.callback_query(lambda c: c.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    session = user_sessions[user_id]

    answer = int(callback.data.split("_")[1])
    q = session["questions"][session["current"]]

    # удаляем прошлое сообщение
    try:
        await bot.delete_message(user_id, session["last_message_id"])
    except:
        pass

    if answer == q["correct"]:
        session["score"] += 1

    session["current"] += 1

    if session["current"] < len(session["questions"]):
        await send_question(user_id)
    else:
        score = session["score"]
        await save_result(user_id, score)

        await bot.send_message(
            user_id,
            f"🎉 Тест завершён!\n\n"
            f"Результат: {score}/{len(session['questions'])}"
        )

        del user_sessions[user_id]

    await callback.answer()
@dp.callback_query(lambda c: c.data == "back")
async def go_back(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    session = user_sessions[user_id]

    if session["current"] > 0:
        session["current"] -= 1
        session["score"] = 0

        # пересчитываем баллы заново
        for i in range(session["current"]):
            if session["answers"][i] == session["questions"][i]["correct"]:
                session["score"] += 1

        session["answers"] = session["answers"][:session["current"]]

        await send_question(user_id)

    await callback.answer()

# Статистика
@dp.callback_query(lambda c: c.data == "stats")
async def stats(callback: types.CallbackQuery):
    data = await get_stats(callback.from_user.id)
    if data:
        tests, score = data
        await callback.message.answer(
            f"📊 Пройдено тестов: {tests}\n"
            f"Общий балл: {score}"
        )
    await callback.answer()

# Теория
@dp.callback_query(lambda c: c.data == "theory")
async def theory(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="СССР", callback_data="ussr")],
        [InlineKeyboardButton(text="Империя", callback_data="empire")],
        [InlineKeyboardButton(text="Древняя Русь", callback_data="rus")],
        [InlineKeyboardButton(text="Всемирная", callback_data="world")]
    ])
    await callback.message.answer("Выберите раздел:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(lambda c: c.data in theory_text)
async def show_theory(callback: types.CallbackQuery):
    await callback.message.answer(theory_text[callback.data])
    await callback.answer()

# Админка
@dp.message(Command("admin"))
async def admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Админ-панель\n\n/users — статистика")


WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "supersecret")

async def on_startup(app):
    webhook_url = os.getenv("RAILWAY_STATIC_URL")
    if not webhook_url:
        webhook_url = os.getenv("RENDER_EXTERNAL_URL")
    if not webhook_url:
        webhook_url = os.getenv("PUBLIC_URL")

    webhook_url = f"{webhook_url}{WEBHOOK_PATH}"

    await bot.set_webhook(
        webhook_url,
        secret_token=WEBHOOK_SECRET
    )
    print(f"Webhook set to {webhook_url}")

async def on_shutdown(app):
    await bot.delete_webhook()
    print("Webhook deleted")

async def handle_webhook(request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return web.Response(status=403)

    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return web.Response()

def create_app():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
