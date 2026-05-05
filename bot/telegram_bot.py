import asyncio
import os
if os.name == "nt":
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

from bot.config import BOT_TOKEN, API_URL, INTERNAL_API_KEY

from aiogram.types import Message, CallbackQuery


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class RequestCompany(StatesGroup):
    waiting_for_inn = State()


# ---------------- MENUS ----------------

director_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Менеджеры")],
        [KeyboardButton(text="🏢 Доступ к юрлицам")],
        [KeyboardButton(text="💰 Балансы")]
    ],
    resize_keyboard=True
)
# ---------------- API helper ----------------

def _api_headers():
    headers = {}
    if INTERNAL_API_KEY:
        headers["X-API-Key"] = INTERNAL_API_KEY
    return headers


manager_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Компании")],
        [KeyboardButton(text="➕ Запросить доступ")]
    ],
    resize_keyboard=True
)


# ---------------- START ----------------

@dp.message(Command("start"))
async def start_handler(message: Message):

    telegram_id = message.from_user.id
    username = message.from_user.username

    # --- регистрация / получение статуса
    response = requests.post(
        f"{API_URL}/telegram/register",
        params={
            "telegram_id": telegram_id,
            "username": username
        },
        headers=_api_headers(),
    )

    data = response.json()
    status = data.get("status")

    # avoid noisy stdout logs in production

    # -------------------------
    # ❗ НОВЫЙ / НЕОДОБРЕННЫЙ
    # -------------------------
    if status in ["pending_approval", "created"]:

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📨 Отправить запрос директору",
                        callback_data="send_user_request_simple"
                    )
                ]
            ]
        )

        await message.answer(
            "Вы не подключены к системе.\nОтправить запрос директору?",
            reply_markup=keyboard
        )
        return

    # -------------------------
    # ❗ ПРОВЕРКА РОЛИ
    # -------------------------
    role_resp = requests.get(
        f"{API_URL}/telegram/user_role",
        params={"telegram_id": telegram_id},
        headers=_api_headers(),
    )

    role_data = role_resp.json()
    role = role_data.get("role")

    # avoid noisy stdout logs in production

    # ❗ если роли нет — НЕ ПУСКАЕМ
    if not role:
        await message.answer(
            "❌ Вы не активированы.\nДождитесь одобрения директора."
        )
        return

    # -------------------------
    # DIRECTOR
    # -------------------------
    if role == "director":
        await message.answer(
            "Вы вошли как директор",
            reply_markup=director_menu
        )
        return

    # -------------------------
    # MANAGER
    # -------------------------
    if role == "manager":
        await message.answer(
            "Вы вошли как менеджер",
            reply_markup=manager_menu
        )
        return

    # fallback
    await message.answer("❌ Неизвестная роль")


# ---------------- МОИ КОМПАНИИ ----------------

@dp.message(lambda m: m.text == "📊 Компании")
async def companies_handler(message: types.Message):

    telegram_id = message.from_user.id

    response = requests.get(
        f"{API_URL}/telegram/my_companies",
        params={"telegram_id": telegram_id},
        headers=_api_headers(),
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



#____________________краткие операции____________________
@dp.callback_query(lambda c: c.data.startswith("period"))
async def show_operations(callback: types.CallbackQuery):

    _, inn, days = callback.data.split(":")

    telegram_id = callback.from_user.id

    response = requests.get(
        f"{API_URL}/telegram/company_operations",
        params={
            "telegram_id": telegram_id,
            "inn": inn,
            "days": days
        },
        headers=_api_headers(),
    )

    data = response.json()

    # 🔴 НЕТ ДОСТУПА
    if data.get("error") == "access_denied":
        await callback.message.edit_text(
            "🔒 У вас нет доступа к этому юрлицу"
        )
        await callback.answer()
        return

    operations = data.get("operations", [])
    name = data.get("company_name", "Компания")

    # 🟡 НЕТ ОПЕРАЦИЙ
    if not operations:
        await callback.message.edit_text(
            f"{name}\n\n❌ За {days} дней нет операций"
        )
        await callback.answer()
        return

    text = f"{name}\nза {days} дней\n\n"

    for op in operations[:10]:
        sign = "+" if op["direction"] == "incoming" else "-"
        text += f"{op['date']}  {sign}{op['amount']}\n"

    text += "\n"
    text += f"Входящие: {data.get('total_in', 0)}\n"
    text += f"Исходящие: {data.get('total_out', 0)}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Показать детали",
                    callback_data=f"details:{inn}:{days}"
                )
            ]
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

#____________________детали операций____________________
@dp.callback_query(lambda c: c.data.startswith("details"))
async def show_details(callback: types.CallbackQuery):

    _, inn, days = callback.data.split(":")

    telegram_id = callback.from_user.id

    response = requests.get(
        f"{API_URL}/telegram/company_operations",
        params={
            "telegram_id": telegram_id,
            "inn": inn,
            "days": days,
            "details": True
        },
        headers=_api_headers(),
    )

    data = response.json()

    # 🔴 НЕТ ДОСТУПА
    if data.get("error") == "access_denied":
        await callback.message.edit_text(
            "🔒 У вас нет доступа к этому юрлицу"
        )
        await callback.answer()
        return

    name = data.get("company_name", "Компания")
    operations = data.get("operations", [])

    # 🟡 НЕТ ОПЕРАЦИЙ
    if not operations:
        await callback.message.edit_text(
            f"{name}\n\n❌ Нет операций"
        )
        await callback.answer()
        return

    text = f"{name}\nдетали\n\n"

    for op in operations[:10]:
        sign = "+" if op["direction"] == "incoming" else "-"
        text += f"{op['date']} {sign}{op['amount']}\n"
        text += f"{op['description']}\n\n"

    await callback.message.edit_text(text)
    await callback.answer()

#____________________компания____________________

@dp.callback_query(lambda c: c.data.startswith("company"))
async def company_selected(callback: types.CallbackQuery):

    _, inn = callback.data.split(":")

    telegram_id = callback.from_user.id

    response = requests.get(
        f"{API_URL}/telegram/my_companies",
        params={"telegram_id": telegram_id},
        headers=_api_headers(),
    )

    companies = response.json()

    name = "Компания"

    for c in companies:
        if c["inn"] == inn:
            name = c["name"]
            break

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 день", callback_data=f"period:{inn}:1"),
                InlineKeyboardButton(text="5 дней", callback_data=f"period:{inn}:5"),
                InlineKeyboardButton(text="30 дней", callback_data=f"period:{inn}:30")
            ]
        ]
    )

    await callback.message.edit_text(
        f"{name}\n\nВыберите период:",
        reply_markup=keyboard
    )

    await callback.answer()

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
        f"{API_URL}/telegram/track",
        params={
            "telegram_id": telegram_id,
            "inn": inn
        },
        headers=_api_headers(),
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
        f"{API_URL}/telegram/request_info",
        params={"request_id": request_id},
        headers=_api_headers(),
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

    directors = requests.get(f"{API_URL}/telegram/directors", headers=_api_headers()).json()

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
            f"{API_URL}/telegram/requests/{request_id}/approve",
            params={"director_id": telegram_id},
            headers=_api_headers(),
        )

        data = response.json()

        name = data.get("company_name")

        text = f"✅ Доступ к компании {name} (ИНН {data['inn']}) одобрен"

    else:

        response = requests.post(
            f"{API_URL}/telegram/requests/{request_id}/reject",
            params={"director_id": telegram_id},
            headers=_api_headers(),
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

    response = requests.get(f"{API_URL}/telegram/managers_companies", headers=_api_headers())

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

    response = requests.get(
        f"{API_URL}/telegram/managers_companies",
        headers=_api_headers(),
    )

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
            f"{API_URL}/telegram/revoke_access",
            params={"tracked_id": tracked_id},
            headers=_api_headers(),
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

#_________________ отрисовка КНОПКИ доступ к юрлицам ______________________
async def render_legal_entities(callback: CallbackQuery, user_id: str):

    resp = requests.get(
        f"{API_URL}/telegram/users/{user_id}/legal_entities",
        headers=_api_headers()
    )

    if resp.status_code != 200:
        await callback.message.answer("Ошибка загрузки юрлиц")
        return

    entities = resp.json()

    keyboard = []

    for i, e in enumerate(entities):
        mark = "✅" if e["has_access"] else "⬜"

        keyboard.append([
            InlineKeyboardButton(
                text=f"{mark} {e['name']}",
                callback_data=f"tle:{user_id}:{i}"   # ✅ коротко
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="Сохранить",
            callback_data=f"save_le:{user_id}"
        )
    ])

    await callback.message.edit_text(
        "Выберите доступ:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

#_________________ ОБРАБОТЧИК КНОПКИ доступ к юрлицам ______________________

@dp.message(lambda message: message.text == "🏢 Доступ к юрлицам")
async def legal_entities_menu(message: Message):

    try:
        response = requests.get(f"{API_URL}/telegram/users", headers=_api_headers())

        users = response.json()

    except Exception as e:
        await message.answer(f"Ошибка запроса к API: {e}")
        return

    if not users:
        await message.answer("❌ Пользователи не найдены")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for user in users:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=user["name"] or "Без имени",
                callback_data=f"le_user:{user['user_id']}"
            )
        ])

    await message.answer("Выберите пользователя:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("le_user:"))
async def select_user(callback: CallbackQuery):

    user_id = callback.data.split(":")[1]

    await render_legal_entities(callback, user_id)

    await callback.answer()

#_________________________ ОБРАБОТЧИК КНОПКИ toggle доступа к юрлицам ______________________

@dp.callback_query(lambda c: c.data.startswith("tle:"))
async def toggle_access(callback: CallbackQuery):

    _, user_id, index = callback.data.split(":")
    index = int(index)

    # получаем список юрлиц
    resp = requests.get(
        f"{API_URL}/telegram/users/{user_id}/legal_entities",
        headers=_api_headers()
    )

    if resp.status_code != 200:
        await callback.answer("Ошибка загрузки")
        return

    data = resp.json()

    # берём entity по индексу
    entity = data[index]
    entity_id = entity["legal_entity_id"]

    # текущие доступы
    current_ids = [
        str(e["legal_entity_id"])
        for e in data if e["has_access"]
    ]

    # toggle
    if str(entity_id) in current_ids:
        current_ids.remove(str(entity_id))
    else:
        current_ids.append(str(entity_id))

    # сохраняем
    requests.post(
        f"{API_URL}/telegram/users/{user_id}/legal_entities",
        json=current_ids,
        headers=_api_headers(),
    )

    await render_legal_entities(callback, user_id)
    await callback.answer()
# ---------------- Новый менеджер ----------------


# ---------------- Обработчик для директора ----------------
@dp.callback_query(lambda c: c.data.startswith("onboard"))
async def onboard_user(callback: CallbackQuery):

    _, telegram_id = callback.data.split(":")

    users = requests.get(f"{API_URL}/telegram/users", headers=_api_headers()).json()

    user = next(
        (u for u in users if str(u["telegram_id"]) == str(telegram_id)),
        None
    )

    if not user:
        await callback.answer("Пользователь не найден")
        return

    user_id = user["user_id"]

    await render_legal_entities(callback, user_id)

    await callback.answer()

# ---------------- Обработчик ----------------

@dp.callback_query(lambda c: c.data == "send_user_request_simple")
async def send_simple_request(callback: CallbackQuery):

    username = callback.from_user.username
    telegram_id = callback.from_user.id

    text = f"📨 Менеджер @{username} просит доступ"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Выбрать доступ",
                    callback_data=f"onboard:{telegram_id}"
                )
            ]
        ]
    )

    directors = requests.get(f"{API_URL}/telegram/directors", headers=_api_headers()).json()

    for director in directors:
        await bot.send_message(
            director["telegram_id"],
            text,
            reply_markup=keyboard
        )

    await callback.message.edit_text("Запрос отправлен")
    await callback.answer()
#___________________кнопка сохранить______________

@dp.callback_query(lambda c: c.data.startswith("save_le:"))
async def save_legal_entities(callback: CallbackQuery):

    _, user_id = callback.data.split(":")

    # --- получаем текущие выбранные юрлица
    resp = requests.get(
        f"{API_URL}/telegram/users/{user_id}/legal_entities",
        headers=_api_headers(),
    )

    if resp.status_code != 200:
        await callback.message.answer("Ошибка загрузки юрлиц")
        return

    entities = resp.json()

    selected_ids = [
        e["legal_entity_id"]
        for e in entities if e["has_access"]
    ]

    # --- сохраняем доступы
    requests.post(
        f"{API_URL}/telegram/users/{user_id}/legal_entities",
        json=selected_ids,
        headers=_api_headers(),
    )

    # --- подтверждаем регистрацию (если новый пользователь)
    pending = requests.get(f"{API_URL}/telegram/users/pending", headers=_api_headers()).json()

    user_request = next(
        (r for r in pending if str(r["user_id"]) == str(user_id)),
        None
    )

    if user_request:
        requests.post(
            f"{API_URL}/telegram/users/{user_request['request_id']}/approve",
            params={"director_telegram_id": callback.from_user.id},
            headers=_api_headers(),
        )

        if user_request.get("telegram_id"):
            await bot.send_message(
                user_request["telegram_id"],
                "✅ Вы добавлены в систему"
            )

    await callback.message.edit_text("✅ Доступ сохранён")
    await callback.answer()


# ---------------- BALANCES (director) ----------------

@dp.message(lambda m: m.text == "💰 Балансы")
async def balances_handler(message: types.Message):
    def _fmt_money(v, currency: str | None = None) -> str:
        if v is None:
            return "—"
        try:
            # handle numbers/strings like "12345.67"
            s = f"{float(v):,.2f}".replace(",", " ").replace(".00", "")
        except Exception:
            s = str(v)
        if currency:
            return f"{s} {currency}"
        return s

    def _fmt_sber_amount(obj) -> tuple[str | None, str]:
        if not isinstance(obj, dict):
            return None, _fmt_money(obj)
        cur = obj.get("currencyName") or obj.get("currency") or ""
        return cur, _fmt_money(obj.get("amount"), cur)

    try:
        resp = requests.get(f"{API_URL}/balances/", headers=_api_headers(), timeout=90)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        await message.answer(f"❌ Не удалось получить балансы: {e}")
        return

    lines = []
    lines.append(f"⏱ Запрос: {data.get('requested_at_utc', '-')}")

    tochka = data.get("tochka") or {}
    if "error" in tochka:
        lines.append(f"\nТочка: ❌ {tochka['error']}")
    else:
        accounts = (tochka.get("accounts") or [])
        if not accounts:
            lines.append("\nТочка: нет счетов/данных")
        else:
            lines.append("\nТочка:")
            for a in accounts:
                acc = a.get("account_number")
                cur = a.get("currency") or "RUB"
                start_b = _fmt_money(a.get("start_balance"), cur)
                end_b = _fmt_money(a.get("end_balance"), cur)
                bank_ts = a.get("bank_timestamp") or "—"
                lines.append(f"- {acc}: {end_b} (на начало: {start_b}, банк: {bank_ts})")

    sber = data.get("sber") or {}
    if "error" in sber:
        lines.append(f"\nСбер: ❌ {sber['error']}")
    else:
        lines.append("\nСбер:")
        acc = sber.get("account_number")
        ts = sber.get("bank_timestamp")
        bal = sber.get("balances") or {}
        if bal:
            opening = bal.get("openingBalance") or bal.get("startBalance")
            closing = bal.get("closingBalance") or bal.get("endBalance")
            credit = bal.get("creditTurnover") or bal.get("incomingTurnover")
            debit = bal.get("debitTurnover") or bal.get("outgoingTurnover")

            _, opening_s = _fmt_sber_amount(opening)
            _, closing_s = _fmt_sber_amount(closing)
            _, credit_s = _fmt_sber_amount(credit)
            _, debit_s = _fmt_sber_amount(debit)

            lines.append(f"- Счёт: {acc}")
            lines.append(f"  На начало: {opening_s}")
            lines.append(f"  На конец: {closing_s}")
            lines.append(f"  Поступления: {credit_s}")
            lines.append(f"  Списания: {debit_s}")
            lines.append(f"  Время банка: {ts or '—'}")
        else:
            lines.append(f"- {acc}: summary получен (время банка: {ts})")

    await message.answer("\n".join(lines))

# ---------------- ЗАПУСК БОТА ----------------

async def main():

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


# if __name__ == "__main__":
#     asyncio.run(main())
asyncio.run(main())