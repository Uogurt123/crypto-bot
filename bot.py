import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import os

BOT_TOKEN = os.getenv("8027726911:AAFQpdzVfXL81mKADRBKyIOXGKS2ItPMNiE")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Хранилище языков и алертов
user_languages = {}
alerts = {}

COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "TON": "the-open-network",
    "SOL": "solana",
    "BNB": "binancecoin",
    "USDT": "tether",
}

# ─── Тексты на двух языках ───
TEXTS = {
    "ru": {
        "start": "👋 Привет! Я крипто-бот.\n\nСлежу за курсами и уведомляю когда цена достигнет нужной отметки 🚀",
        "prices": "📊 Курсы монет",
        "alerts": "🔔 Уведомления",
        "info": "ℹ️ Информация",
        "donate": "☘️ Донат",
        "language": "🌍 Язык",
        "loading": "⏳ Загружаю курсы...",
        "prices_title": "📊 *Текущие курсы:*\n\n",
        "updated": "\n_Обновлено только что_",
        "error": "❌ Ошибка при загрузке курсов. Попробуй позже.",
        "alerts_title": "🔔 *Уведомления*\n\nАктивных алертов: ",
        "add_alert": "➕ Добавить алерт",
        "my_alerts": "📋 Мои алерты",
        "choose_coin": "Выбери монету:",
        "enter_price": "✅ Монета: *{coin}*\n\nВведи цену в USD (например: `45000`):",
        "enter_number": "❌ Введи число, например: `45000`",
        "when_notify": "Цена: *${price}*\n\nКогда уведомить?",
        "above": "📈 Выше цены",
        "below": "📉 Ниже цены",
        "alert_created": "✅ Алерт создан!\n\n{arrow} *{coin}* — уведомлю когда цена будет {dir} *${price}*",
        "above_text": "выше",
        "below_text": "ниже",
        "no_alerts": "📋 У тебя нет активных алертов.\n\nДобавь первый!",
        "alerts_list": "📋 *Твои алерты:*\n\n",
        "delete": "❌ Удалить #",
        "alert_deleted": "✅ Алерт удалён!",
        "alert_fired": "🔔 *Алерт сработал!*\n\n{arrow} *{coin}* достиг ${current}\nТвоя цель: ${target}",
        "info_text": "ℹ️ *О боте*\n\nСоздатель: @aquaee\nКанал: скоро\n\nБот показывает курсы криптовалют и присылает уведомления когда цена достигает нужной отметки.",
        "donate_text": "☘️ *Поддержать проект*\n\nTON кошелёк:\n`UQArVnAPk0F6LqrGv3Zx1RPbUeW0SWeI9Ab1M9i81Fci7bKW`\n\nСпасибо! 🙏",
        "choose_language": "🌍 Выбери язык:",
        "language_set": "✅ Язык изменён на Русский!",
        "back": "◀️ Назад",
    },
    "en": {
        "start": "👋 Hello! I'm a crypto bot.\n\nI track prices and notify you when a price hits your target 🚀",
        "prices": "📊 Prices",
        "alerts": "🔔 Alerts",
        "info": "ℹ️ Info",
        "donate": "☘️ Donate",
        "language": "🌍 Language",
        "loading": "⏳ Loading prices...",
        "prices_title": "📊 *Current prices:*\n\n",
        "updated": "\n_Just updated_",
        "error": "❌ Error loading prices. Try again later.",
        "alerts_title": "🔔 *Alerts*\n\nActive alerts: ",
        "add_alert": "➕ Add alert",
        "my_alerts": "📋 My alerts",
        "choose_coin": "Choose a coin:",
        "enter_price": "✅ Coin: *{coin}*\n\nEnter price in USD (e.g. `45000`):",
        "enter_number": "❌ Enter a number, e.g. `45000`",
        "when_notify": "Price: *${price}*\n\nWhen to notify?",
        "above": "📈 Above price",
        "below": "📉 Below price",
        "alert_created": "✅ Alert created!\n\n{arrow} *{coin}* — will notify when price is {dir} *${price}*",
        "above_text": "above",
        "below_text": "below",
        "no_alerts": "📋 You have no active alerts.\n\nAdd your first one!",
        "alerts_list": "📋 *Your alerts:*\n\n",
        "delete": "❌ Delete #",
        "alert_deleted": "✅ Alert deleted!",
        "alert_fired": "🔔 *Alert triggered!*\n\n{arrow} *{coin}* reached ${current}\nYour target: ${target}",
        "info_text": "ℹ️ *About bot*\n\nCreator: @aquaee\nChannel: coming soon\n\nThis bot shows crypto prices and sends alerts when price hits your target.",
        "donate_text": "☘️ *Support the project*\n\nTON wallet:\n`UQArVnAPk0F6LqrGv3Zx1RPbUeW0SWeI9Ab1M9i81Fci7bKW`\n\nThank you! 🙏",
        "choose_language": "🌍 Choose language:",
        "language_set": "✅ Language changed to English!",
        "back": "◀️ Back",
    }
}

def t(user_id, key):
    lang = user_languages.get(user_id, "ru")
    return TEXTS[lang][key]

class AlertState(StatesGroup):
    waiting_coin = State()
    waiting_price = State()
    waiting_direction = State()

def main_keyboard(user_id):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(user_id, "prices")), KeyboardButton(text=t(user_id, "alerts"))],
            [KeyboardButton(text=t(user_id, "info")), KeyboardButton(text=t(user_id, "donate"))],
            [KeyboardButton(text=t(user_id, "language"))],
        ],
        resize_keyboard=True
    )

async def get_prices():
    ids = ",".join(COINS.values())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

# ─── /start ───
@dp.message(CommandStart())
async def start(message: Message):
    uid = message.from_user.id
    await message.answer(t(uid, "start"), reply_markup=main_keyboard(uid))

# ─── Курсы ───
@dp.message(F.text.in_(["📊 Курсы монет", "📊 Prices"]))
async def show_prices(message: Message):
    uid = message.from_user.id
    await message.answer(t(uid, "loading"))
    try:
        data = await get_prices()
        text = t(uid, "prices_title")
        for symbol, coin_id in COINS.items():
            price = data[coin_id]["usd"]
            change = data[coin_id]["usd_24h_change"]
            arrow = "🟢" if change >= 0 else "🔴"
            text += f"{arrow} *{symbol}*: ${price:,.2f}  ({change:+.2f}%)\n"
        text += t(uid, "updated")
        await message.answer(text, parse_mode="Markdown")
    except Exception:
        await message.answer(t(uid, "error"))

# ─── Уведомления ───
@dp.message(F.text.in_(["🔔 Уведомления", "🔔 Alerts"]))
async def alerts_menu(message: Message):
    uid = message.from_user.id
    user_alerts = alerts.get(uid, [])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "add_alert"), callback_data="add_alert")],
        [InlineKeyboardButton(text=t(uid, "my_alerts"), callback_data="my_alerts")],
    ])
    await message.answer(t(uid, "alerts_title") + str(len(user_alerts)), parse_mode="Markdown", reply_markup=keyboard)

# ─── Добавить алерт шаг 1 ───
@dp.callback_query(F.data == "add_alert")
async def add_alert_step1(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s, callback_data=f"coin_{s}") for s in list(COINS.keys())[:3]],
        [InlineKeyboardButton(text=s, callback_data=f"coin_{s}") for s in list(COINS.keys())[3:]],
    ])
    await call.message.edit_text(t(uid, "choose_coin"), reply_markup=keyboard)
    await state.set_state(AlertState.waiting_coin)

# ─── Шаг 2 ───
@dp.callback_query(F.data.startswith("coin_"))
async def add_alert_step2(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    coin = call.data.replace("coin_", "")
    await state.update_data(coin=coin)
    await call.message.edit_text(t(uid, "enter_price").format(coin=coin), parse_mode="Markdown")
    await state.set_state(AlertState.waiting_price)

# ─── Шаг 3 ───
@dp.message(AlertState.waiting_price)
async def add_alert_step3(message: Message, state: FSMContext):
    uid = message.from_user.id
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer(t(uid, "enter_number"), parse_mode="Markdown")
        return
    await state.update_data(price=price)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(uid, "above"), callback_data="dir_above")],
        [InlineKeyboardButton(text=t(uid, "below"), callback_data="dir_below")],
    ])
    await message.answer(t(uid, "when_notify").format(price=f"{price:,.2f}"), parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(AlertState.waiting_direction)

# ─── Шаг 4 ───
@dp.callback_query(F.data.startswith("dir_"))
async def add_alert_step4(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    direction = "above" if call.data == "dir_above" else "below"
    data = await state.get_data()
    if uid not in alerts:
        alerts[uid] = []
    alerts[uid].append({"coin": data["coin"], "price": data["price"], "direction": direction})
    arrow = "📈" if direction == "above" else "📉"
    dir_text = t(uid, "above_text") if direction == "above" else t(uid, "below_text")
    await call.message.edit_text(
        t(uid, "alert_created").format(arrow=arrow, coin=data["coin"], dir=dir_text, price=f"{data['price']:,.2f}"),
        parse_mode="Markdown"
    )
    await state.clear()

# ─── Мои алерты ───
@dp.callback_query(F.data == "my_alerts")
async def show_alerts(call: CallbackQuery):
    uid = call.from_user.id
    user_alerts = alerts.get(uid, [])
    if not user_alerts:
        await call.message.edit_text(t(uid, "no_alerts"))
        return
    text = t(uid, "alerts_list")
    buttons = []
    for i, a in enumerate(user_alerts):
        arrow = "📈" if a["direction"] == "above" else "📉"
        dir_text = t(uid, "above_text") if a["direction"] == "above" else t(uid, "below_text")
        text += f"{i+1}. {arrow} *{a['coin']}* {dir_text} ${a['price']:,.2f}\n"
        buttons.append([InlineKeyboardButton(text=t(uid, "delete") + str(i+1), callback_data=f"del_{i}")])
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ─── Удалить алерт ───
@dp.callback_query(F.data.startswith("del_"))
async def delete_alert(call: CallbackQuery):
    uid = call.from_user.id
    index = int(call.data.replace("del_", ""))
    if uid in alerts and index < len(alerts[uid]):
        alerts[uid].pop(index)
    await call.answer(t(uid, "alert_deleted"))
    await show_alerts(call)

# ─── Информация ───
@dp.message(F.text.in_(["ℹ️ Информация", "ℹ️ Info"]))
async def info(message: Message):
    uid = message.from_user.id
    await message.answer(t(uid, "info_text"), parse_mode="Markdown")

# ─── Донат ───
@dp.message(F.text.in_(["☘️ Донат", "☘️ Donate"]))
async def donate(message: Message):
    uid = message.from_user.id
    await message.answer(t(uid, "donate_text"), parse_mode="Markdown")

# ─── Язык ───
@dp.message(F.text == "🌍 Язык" )
async def language_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
    ])
    await message.answer(t(message.from_user.id, "choose_language"), reply_markup=keyboard)

@dp.message(F.text == "🌍 Language")
async def language_menu_en(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
    ])
    await message.answer(t(message.from_user.id, "choose_language"), reply_markup=keyboard)

@dp.callback_query(F.data.startswith("lang_"))
async def set_language(call: CallbackQuery):
    uid = call.from_user.id
    lang = call.data.replace("lang_", "")
    user_languages[uid] = lang
    await call.message.edit_text(t(uid, "language_set"))
    await call.message.answer(t(uid, "start"), reply_markup=main_keyboard(uid))

# ─── Фоновая проверка алертов ───
async def check_alerts():
    while True:
        await asyncio.sleep(60)
        if not alerts:
            continue
        try:
            data = await get_prices()
            for uid, user_alerts in list(alerts.items()):
                to_remove = []
                for i, alert in enumerate(user_alerts):
                    coin_id = COINS.get(alert["coin"])
                    if not coin_id:
                        continue
                    current_price = data[coin_id]["usd"]
                    triggered = (
                        alert["direction"] == "above" and current_price >= alert["price"] or
                        alert["direction"] == "below" and current_price <= alert["price"]
                    )
                    if triggered:
                        arrow = "📈" if alert["direction"] == "above" else "📉"
                        await bot.send_message(
                            uid,
                            t(uid, "alert_fired").format(
                                arrow=arrow,
                                coin=alert["coin"],
                                current=f"{current_price:,.2f}",
                                target=f"{alert['price']:,.2f}"
                            ),
                            parse_mode="Markdown"
                        )
                        to_remove.append(i)
                for i in reversed(to_remove):
                    user_alerts.pop(i)
        except Exception:
            pass

async def main():
    asyncio.create_task(check_alerts())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    waiting_coin = State()
    waiting_price = State()
    waiting_direction = State()

# ─── Клавиатура снизу ───
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Курсы монет"), KeyboardButton(text="🔔 Уведомления")],
            [KeyboardButton(text="ℹ️ Информация"), KeyboardButton(text="☘️ Донат")],
        ],
        resize_keyboard=True
    )

# ─── Получить курсы с CoinGecko ───
async def get_prices():
    ids = ",".join(COINS.values())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

# ─── /start ───
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 Привет! Я крипто-бот.\n\n"
        "Слежу за курсами и уведомляю когда цена достигнет нужной отметки 🚀",
        reply_markup=main_keyboard()
    )

# ─── Курсы монет ───
@dp.message(F.text == "📊 Курсы монет")
async def show_prices(message: Message):
    await message.answer("⏳ Загружаю курсы...")
    try:
        data = await get_prices()
        text = "📊 *Текущие курсы:*\n\n"
        for symbol, coin_id in COINS.items():
            price = data[coin_id]["usd"]
            change = data[coin_id]["usd_24h_change"]
            arrow = "🟢" if change >= 0 else "🔴"
            text += f"{arrow} *{symbol}*: ${price:,.2f}  ({change:+.2f}%)\n"
        text += "\n_Обновлено только что_"
        await message.answer(text, parse_mode="Markdown")
    except Exception:
        await message.answer("❌ Ошибка при загрузке курсов. Попробуй позже.")

# ─── Уведомления — главное меню ───
@dp.message(F.text == "🔔 Уведомления")
async def alerts_menu(message: Message):
    user_id = message.from_user.id
    user_alerts = alerts.get(user_id, [])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить алерт", callback_data="add_alert")],
        [InlineKeyboardButton(text="📋 Мои алерты", callback_data="my_alerts")],
    ])

    text = f"🔔 *Уведомления*\n\nАктивных алертов: {len(user_alerts)}"
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

# ─── Добавить алерт — шаг 1 ───
@dp.callback_query(F.data == "add_alert")
async def add_alert_step1(call: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s, callback_data=f"coin_{s}") for s in list(COINS.keys())[:3]],
        [InlineKeyboardButton(text=s, callback_data=f"coin_{s}") for s in list(COINS.keys())[3:]],
    ])
    await call.message.edit_text("Выбери монету:", reply_markup=keyboard)
    await state.set_state(AlertState.waiting_coin)

# ─── Шаг 2 — выбрали монету ───
@dp.callback_query(F.data.startswith("coin_"))
async def add_alert_step2(call: CallbackQuery, state: FSMContext):
    coin = call.data.replace("coin_", "")
    await state.update_data(coin=coin)
    await call.message.edit_text(f"✅ Монета: *{coin}*\n\nВведи цену в USD (например: `45000`):", parse_mode="Markdown")
    await state.set_state(AlertState.waiting_price)

# ─── Шаг 3 — ввели цену ───
@dp.message(AlertState.waiting_price)
async def add_alert_step3(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("❌ Введи число, например: `45000`", parse_mode="Markdown")
        return

    await state.update_data(price=price)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Выше цены", callback_data="dir_above")],
        [InlineKeyboardButton(text="📉 Ниже цены", callback_data="dir_below")],
    ])
    await message.answer(f"Цена: *${price:,.2f}*\n\nКогда уведомить?", parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(AlertState.waiting_direction)

# ─── Шаг 4 — направление, сохраняем алерт ───
@dp.callback_query(F.data.startswith("dir_"))
async def add_alert_step4(call: CallbackQuery, state: FSMContext):
    direction = "above" if call.data == "dir_above" else "below"
    data = await state.get_data()
    user_id = call.from_user.id

    if user_id not in alerts:
        alerts[user_id] = []
    alerts[user_id].append({"coin": data["coin"], "price": data["price"], "direction": direction})

    arrow = "📈" if direction == "above" else "📉"
    dir_text = "выше" if direction == "above" else "ниже"
    await call.message.edit_text(
        f"✅ Алерт создан!\n\n{arrow} *{data['coin']}* — уведомлю когда цена будет {dir_text} *${data['price']:,.2f}*",
        parse_mode="Markdown"
    )
    await state.clear()

# ─── Мои алерты ───
@dp.callback_query(F.data == "my_alerts")
async def show_alerts(call: CallbackQuery):
    user_id = call.from_user.id
    user_alerts = alerts.get(user_id, [])

    if not user_alerts:
        await call.message.edit_text("📋 У тебя нет активных алертов.\n\nДобавь первый!")
        return

    text = "📋 *Твои алерты:*\n\n"
    buttons = []
    for i, a in enumerate(user_alerts):
        arrow = "📈" if a["direction"] == "above" else "📉"
        dir_text = "выше" if a["direction"] == "above" else "ниже"
        text += f"{i+1}. {arrow} *{a['coin']}* {dir_text} ${a['price']:,.2f}\n"
        buttons.append([InlineKeyboardButton(text=f"❌ Удалить #{i+1}", callback_data=f"del_{i}")])

    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ─── Удалить алерт ───
@dp.callback_query(F.data.startswith("del_"))
async def delete_alert(call: CallbackQuery):
    index = int(call.data.replace("del_", ""))
    user_id = call.from_user.id
    if user_id in alerts and index < len(alerts[user_id]):
        alerts[user_id].pop(index)
    await call.answer("✅ Алерт удалён!")
    await show_alerts(call)

# ─── Информация ───
@dp.message(F.text == "ℹ️ Информация")
async def info(message: Message):
    await message.answer(
        "ℹ️ *О боте*\n\n"
        "Создатель: @aquaee\n"
        "Канал: скоро\n\n"
        "Бот показывает курсы криптовалют и присылает уведомления когда цена достигает нужной отметки.",
        parse_mode="Markdown"
    )

# ─── Донат ───
@dp.message(F.text == "☘️ Донат")
async def donate(message: Message):
    await message.answer(
        "☘️ *Поддержать проект*\n\n"
        "TON кошелёк:\n`UQArVnAPk0F6LqrGv3Zx1RPbUeW0SWeI9Ab1M9i81Fci7bKW`\n\n"
        "Спасибо! 🙏",
        parse_mode="Markdown"
    )

# ─── Фоновая проверка алертов каждые 60 секунд ───
async def check_alerts():
    while True:
        await asyncio.sleep(60)
        if not alerts:
            continue
        try:
            data = await get_prices()
            for user_id, user_alerts in list(alerts.items()):
                to_remove = []
                for i, alert in enumerate(user_alerts):
                    coin_id = COINS.get(alert["coin"])
                    if not coin_id:
                        continue
                    current_price = data[coin_id]["usd"]
                    triggered = (
                        alert["direction"] == "above" and current_price >= alert["price"] or
                        alert["direction"] == "below" and current_price <= alert["price"]
                    )
                    if triggered:
                        arrow = "📈" if alert["direction"] == "above" else "📉"
                        await bot.send_message(
                            user_id,
                            f"🔔 *Алерт сработал!*\n\n{arrow} *{alert['coin']}* достиг ${current_price:,.2f}\n"
                            f"Твоя цель: ${alert['price']:,.2f}",
                            parse_mode="Markdown"
                        )
                        to_remove.append(i)
                for i in reversed(to_remove):
                    user_alerts.pop(i)
        except Exception:
            pass

async def main():
    asyncio.create_task(check_alerts())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
