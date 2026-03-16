import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from bot.config import BOT_TOKEN, API_URL


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class RequestCompany(StatesGroup):
    waiting_for_inn = State()


# ---------------- MENUS ----------------

director_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Менеджеры")]
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

        await message.answer(
            "Вы вошли как директор",
            reply_markup=director_menu
        )

    else:

        await message.answer(
            "Добро пожаловать в систему мониторинга операций.",
            reply_markup=manager_menu
        )


# ---------------- МОИ КОМПАНИИ ----------------

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

    await message.answer(
        "Выберите компанию:",
        reply_markup=markup
    )


# ---------------- ЗАПРОС ДОСТУПА ----------------

@dp.message(lambda m: m.text == "➕ Запросить доступ")
async def request_access(message: types.Message, state: FSMContext):

    await state.set_state(RequestCompany.waiting_for_inn)

    await message.answer("Введите ИНН компании.")


# ---------------- ОБРАБОТКА ИНН ----------------

@dp.message(RequestCompany.waiting_for_inn)
async def process_inn(message: types.Message, state: FSMContext):

    inn = "".join(filter(str.isdigit, message.text))
    telegram_id = message.from_user.id

    response = requests.post(
        f"{API_URL}/track",
        params={
            "telegram_id": telegram_id,
            "inn": inn
        }
    )

    data = response.json()

    status = data.get("status")

    if status == "invalid_inn":

        await message.answer(
            "❌ Компания не найдена.\nПроверьте корректность ИНН."
        )

        await state.clear()
        return

    if status == "already_tracking":

        name = data.get("company_name") or "Компания"

        await message.answer(
            f"ℹ️ {name}\nИНН {inn}\n\n"
            "У вас уже есть доступ к этой компании."
        )

        await state.clear()
        return

    request_id = data.get("request_id")

    if not request_id:

        await message.answer("Ошибка создания запроса.")
        await state.clear()
        return

    name = data.get("company_name") or "Компания"
    company_status = data.get("company_status")

    text = f"🏢 {name}\nИНН {inn}"

    if company_status == "new":
        text += "\n\n📌 Статус: новая компания"
    else:
        text += "\n\n📌 Статус: уже есть в системе"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📨 Отправить запрос директору",
                    callback_data=f"send_request:{request_id}"
                )
            ]
        ]
    )

    await message.answer(text, reply_markup=keyboard)

    await state.clear()


# ---------------- ОТПРАВКА ЗАПРОСА ДИРЕКТОРУ ----------------

@dp.callback_query(lambda c: c.data.startswith("send_request"))
async def send_request(callback: types.CallbackQuery):

    request_id = callback.data.split(":")[1]
    username = callback.from_user.username

    response = requests.get(
        f"{API_URL}/request_info",
        params={"request_id": request_id}
    )

    data = response.json()

    company_name = data.get("company_name") or "Компания"
    inn = data.get("inn")
    company_status = data.get("company_status")

    if company_status == "new":
        status_text = "новая компания"
    else:
        status_text = "уже есть в системе"

    text = (
        f"📨 Менеджер @{username} отправил запрос\n\n"
        f"🏢 {company_name}\n"
        f"ИНН: {inn}\n"
        f"Статус: {status_text}"
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

    directors = requests.get(f"{API_URL}/directors").json()

    for director in directors:
        await bot.send_message(
            director["telegram_id"],
            text,
            reply_markup=keyboard
        )

    await callback.message.edit_text("📨 Запрос отправлен директору")
    await callback.answer()

# ---------------- РЕШЕНИЕ ДИРЕКТОРА ----------------

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

        text = f"✅ Доступ к компании {name} (ИНН {data['inn']}) одобрен"

    else:

        response = requests.post(
            f"{API_URL}/requests/{request_id}/reject",
            params={"director_id": telegram_id}
        )

        data = response.json()

        text = f"❌ Доступ к компании {data['inn']} отклонён"

    await bot.send_message(
        data["manager_telegram_id"],
        text
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n" + text
    )

    await callback.answer()


# ---------------- МЕНЕДЖЕРЫ ДЛЯ ДИРЕКТОРА ----------------

@dp.message(lambda m: m.text == "👥 Менеджеры")
async def show_managers(message: types.Message):

    response = requests.get(f"{API_URL}/managers_companies")

    data = response.json()

    if not data:
        await message.answer("Менеджеров нет")
        return

    for manager in data:

        name = manager["manager_name"]
        companies = manager["companies"]

        if not companies:

            text = f"{name}\n(нет активных компаний)"
            await message.answer(text)

        else:

            keyboard = InlineKeyboardMarkup(inline_keyboard=[])

            text = f"Компании менеджера {name}\n"

            for company in companies:

                tracked_id = company["tracked_id"]

                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=f'{company["name"]} ({company["inn"]})',
                        callback_data="ignore"
                    ),
                    InlineKeyboardButton(
                        text="❌ Отозвать",
                        callback_data=f"revoke:{tracked_id}"
                    )
                ])

            await message.answer(text, reply_markup=keyboard)

# ---------------- КОМПАНИИ МЕНЕДЖЕРА ----------------

@dp.callback_query(lambda c: c.data.startswith("manager"))
async def show_manager_companies(callback: types.CallbackQuery):

    manager = callback.data.split(":")[1]

    response = requests.get(f"{API_URL}/managers_companies")

    data = response.json()

    companies = data.get(manager)

    if not companies:
        await callback.message.answer("У менеджера нет компаний.")
        return

    keyboard = []

    for c in companies:

        name = c["name"] or "Компания"
        inn = c["inn"]
        tracked_id = c["tracked_id"]

        keyboard.append([
            InlineKeyboardButton(
                text=f"{name} ({inn})",
                callback_data="ignore"
            ),
            InlineKeyboardButton(
                text="❌ Отозвать",
                callback_data=f"revoke:{tracked_id}"
            )
        ])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.answer(
        f"Компании менеджера {manager}",
        reply_markup=markup
    )

#_________________ ОБРАБОТЧИК КНОПКИ отозвать доступ ______________________

@dp.callback_query(lambda c: c.data.startswith("revoke"))
async def revoke_access(callback: types.CallbackQuery):

    tracked_id = callback.data.split(":")[1]

    try:

        response = requests.post(
            f"{API_URL}/revoke_access",
            params={"tracked_id": tracked_id}
        )

        data = response.json()

    except Exception:
        await callback.answer("Ошибка соединения с сервером")
        return

    name = data.get("company_name") or "Компания"
    inn = data.get("inn", "")

    text = f"❌ Доступ к компании {name} (ИНН {inn}) отозван."

    # изменяем текущее сообщение
    await callback.message.edit_text(
        callback.message.text + "\n\n" + text
    )

    # уведомляем менеджера (если API возвращает telegram_id)
    manager_telegram_id = data.get("manager_telegram_id")

    if manager_telegram_id:

        await bot.send_message(
            manager_telegram_id,
            f"❌ Ваш доступ к компании {name} (ИНН {inn}) был отозван директором."
        )

    await callback.answer()

# ---------------- ЗАПУСК БОТА ----------------

async def main():

    print("Bot started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())