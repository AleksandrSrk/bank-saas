import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import BOT_TOKEN, API_URL


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# получить директоров из API
def get_directors():

    response = requests.get(f"{API_URL}/directors")

    if response.status_code != 200:
        return []

    return response.json()


# регистрация пользователя
@dp.message(Command("start"))
async def start_handler(message: types.Message):

    telegram_id = message.from_user.id
    username = message.from_user.username

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{API_URL}/register",
            params={
                "telegram_id": telegram_id,
                "username": username
            }
        )

    print("REQUEST URL:", f"{API_URL}/register")
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    if response.status_code != 200:
        await message.answer("Ошибка сервера. Попробуйте позже.")
        return

    data = response.json()

    if data["status"] == "registered":
        await message.answer("Вы зарегистрированы в системе.")
    else:
        await message.answer("Вы уже зарегистрированы.")


# запрос отслеживания ИНН
@dp.message(Command("track"))
async def track_handler(message: types.Message):

    parts = message.text.split()

    if len(parts) != 2:
        await message.answer("Использование: /track ИНН")
        return

    inn = parts[1]
    telegram_id = message.from_user.id
    username = message.from_user.username

    response = requests.post(
        f"{API_URL}/track",
        params={
            "telegram_id": telegram_id,
            "inn": inn
        }
    )

    data = response.json()

    if data["status"] != "request_created":
        await message.answer("Ошибка создания запроса")
        return

    request_id = data["request_id"]

    await message.answer(
        f"Запрос на отслеживание ИНН {inn} отправлен директору."
    )

    directors = get_directors()

    for director in directors:

        text = (
            f"Менеджер {username} запросил отслеживание\n\n"
            f"ИНН: {inn}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Одобрить",
                        callback_data=f"approve:{request_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Отклонить",
                        callback_data=f"reject:{request_id}"
                    )
                ]
            ]
        )

        await bot.send_message(
            director["telegram_id"],
            text,
            reply_markup=keyboard
        )


# обработка кнопок approve / reject
@dp.callback_query(lambda c: c.data.startswith("approve") or c.data.startswith("reject"))
async def handle_decision(callback: types.CallbackQuery):

    action, request_id = callback.data.split(":")
    telegram_id = callback.from_user.id

    try:

        if action == "approve":

            response = requests.post(
                f"{API_URL}/requests/{request_id}/approve",
                params={
                    "director_id": telegram_id
                }
            )

            if response.status_code == 200:

                await callback.message.edit_text(
                    callback.message.text + "\n\n✅ ОДОБРЕНО"
                )

            else:
                await callback.answer("Ошибка одобрения", show_alert=True)


        elif action == "reject":

            response = requests.post(
                f"{API_URL}/requests/{request_id}/reject",
                params={
                    "director_id": telegram_id
                }
            )

            if response.status_code == 200:

                await callback.message.edit_text(
                    callback.message.text + "\n\n❌ ОТКЛОНЕНО"
                )

            else:
                await callback.answer("Ошибка отклонения", show_alert=True)

    except Exception as e:

        print("Callback error:", e)
        await callback.answer("Ошибка сервера", show_alert=True)

    await callback.answer()


async def main():

    print("Bot started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())