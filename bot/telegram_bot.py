import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from bot.config import BOT_TOKEN, API_URL


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class RequestCompany(StatesGroup):
    waiting_for_inn = State()


director_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Менеджеры")],
        [KeyboardButton(text="📊 Компании на отслеживании")]
    ],
    resize_keyboard=True
)

manager_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Компании")],
        [KeyboardButton(text="➕ Запросить доступ")]
    ],
    resize_keyboard=True
)


# ---------------- START ----------------

@dp.message(Command("start"))
async def start_handler(message: types.Message):

    telegram_id = message.from_user.id
    username = message.from_user.username

    async with httpx.AsyncClient(timeout=10, trust_env=False) as client:

        await client.post(
            f"{API_URL}/register",
            params={
                "telegram_id": telegram_id,
                "username": username
            }
        )

        role_response = await client.get(
            f"{API_URL}/user_role",
            params={"telegram_id": telegram_id}
        )

    role = role_response.json().get("role")

    if role == "director":
        await message.answer("Вы вошли как директор", reply_markup=director_menu)
    else:
        await message.answer("Добро пожаловать в систему мониторинга операций.", reply_markup=manager_menu)


# ---------------- COMPANIES ----------------

@dp.message(lambda m: m.text == "📊 Компании")
async def companies_handler(message: types.Message):

    telegram_id = message.from_user.id

    response = requests.get(
        f"{API_URL}/my_companies",
        params={"telegram_id": telegram_id}
    )

    companies = response.json()

    if not companies:
        await message.answer("У вас нет компаний на отслеживании.")
        return

    keyboard = []

    for company in companies:

        name = company["name"] or "Без названия"
        inn = company["inn"]

        keyboard.append([
            InlineKeyboardButton(
                text=f"{name} ({inn})",
                callback_data=f"company:{inn}"
            )
        ])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await message.answer("Выберите компанию:", reply_markup=markup)


# ---------------- REQUEST ACCESS ----------------

@dp.message(lambda m: m.text == "➕ Запросить доступ")
async def request_access(message: types.Message, state: FSMContext):

    await state.set_state(RequestCompany.waiting_for_inn)

    await message.answer("Введите ИНН компании.")


@dp.message(RequestCompany.waiting_for_inn)
async def process_inn(message: types.Message, state: FSMContext):

    inn = "".join(filter(str.isdigit, message.text))

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

    if data.get("status") == "already_tracking":

        name = data.get("company_name")

        if name:
            await message.answer(f"Компания {name} уже отслеживается.")
        else:
            await message.answer("Компания уже отслеживается.")

        await state.clear()
        return

    request_id = data["request_id"]

    await message.answer("Запрос отправлен директору.", reply_markup=manager_menu)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{request_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{request_id}")
            ]
        ]
    )

    directors = requests.get(f"{API_URL}/directors").json()

    company_name = data.get("company_name")

    if company_name:
        text = f"Менеджер {username} запросил отслеживание\n\n🏢 {company_name}\nИНН: {inn}"
    else:
        text = f"Менеджер {username} запросил отслеживание\n\nНовая компания\nИНН: {inn}"

    for director in directors:
        await bot.send_message(director["telegram_id"], text, reply_markup=keyboard)

    await state.clear()


# ---------------- APPROVE / REJECT ----------------

@dp.callback_query(lambda c: c.data.startswith("approve") or c.data.startswith("reject"))
async def handle_decision(callback: types.CallbackQuery):

    action, request_id = callback.data.split(":")
    telegram_id = callback.from_user.id

    if action == "approve":

        response = requests.post(
            f"{API_URL}/requests/{request_id}/approve",
            params={"director_id": telegram_id}
        )

        data = response.json()

        name = data.get("company_name")

        if name:
            text = f"✅ Доступ к компании {name} (ИНН {data['inn']}) одобрен"
        else:
            text = f"✅ Доступ к компании {data['inn']} одобрен"

    else:

        response = requests.post(
            f"{API_URL}/requests/{request_id}/reject",
            params={"director_id": telegram_id}
        )

        data = response.json()

        text = f"❌ Доступ к компании {data['inn']} отклонён"

    await bot.send_message(data["manager_telegram_id"], text)

    await callback.message.edit_text(callback.message.text + f"\n\n{text}")

    await callback.answer()


async def main():

    print("Bot started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())