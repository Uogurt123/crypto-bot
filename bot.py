import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8027726911:AAH_l2M7l6NsfBSWiCewueMHmkm8ZwyJJwk"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Хранилище алертов: {user_id: [{"coin": "bitcoin", "price": 50000, "direction": "above"}]}
alerts = {}

COINS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "TON": "the-open-network",
    "SOL": "solana",
    "BNB": "binancecoin",
    "USDT": "tether",
}

class AlertState(StatesGroup):
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
        "Канал: @TreckerCryptooInfo\n\n"
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
