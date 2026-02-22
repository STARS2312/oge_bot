import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import TOKEN, ADMIN_ID
from database import *
from questions import questions
from theory import theory_text
import random

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
async def start_test(callback: types.CallbackQuery):
    selected = random.sample(questions, 15 if len(questions) >= 15 else len(questions))

    user_sessions[callback.from_user.id] = {
        "current": 0,
        "score": 0,
        "questions": selected,
        "answers": []
    }

    await send_question(callback.from_user.id)
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

    # Кнопка назад
    if session["current"] > 0:
        buttons.append(
            [InlineKeyboardButton(text="⬅ Назад", callback_data="back")]
        )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await bot.send_message(
        user_id,
        f"📘 Вопрос {session['current'] + 1}/{len(session['questions'])}\n\n{q['question']}",
        reply_markup=kb
    )
# Ответ
@dp.callback_query(lambda c: c.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    session = user_sessions[user_id]

    answer = int(callback.data.split("_")[1])
    q = session["questions"][session["current"]]

    session["answers"].append(answer)

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
            f"🎉 Тест завершён!\n\nВаш результат: {score}/{len(session['questions'])}"
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

# Запуск
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
