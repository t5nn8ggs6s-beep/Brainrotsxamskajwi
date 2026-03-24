import json, asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup, PreCheckoutQuery, ContentType
from config import TOKEN, CHANNEL, ADMINS, CURRENCY

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Загрузка продуктов
with open("products.json", encoding="utf-8") as f:
    PRODUCTS = json.load(f)

# Загрузка/сохранение базы
try:
    with open("database.json", encoding="utf-8") as f:
        DB = json.load(f)
except:
    DB = {"users": {}}

def save_db():
    with open("database.json", "w", encoding="utf-8") as f:
        json.dump(DB, f, ensure_ascii=False, indent=2)

# Проверка подписки
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status != "left"
    except:
        return False

# /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    if not await check_sub(message.from_user.id):
        await message.answer(f"❗ Подпишись на канал {CHANNEL}, чтобы использовать бот!")
        return
    
    if user_id not in DB["users"]:
        DB["users"][user_id] = {"balance": 0, "purchases": []}
        save_db()
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🛒 Хапи Шоп", "💰 Баланс")
    if message.from_user.id in ADMINS:
        kb.add("👑 Админка")
    await message.answer("🎉 Добро пожаловать в Хапи Шоп!", reply_markup=kb)

# Баланс
@dp.message_handler(lambda m: m.text == "💰 Баланс")
async def balance(message: types.Message):
    user = DB["users"].get(str(message.from_user.id))
    await message.answer(f"💎 У тебя {user['balance']}⭐\n🎁 Покупки: {len(user['purchases'])}")

# Магазин с эмодзи
@dp.message_handler(lambda m: m.text == "🛒 Хапи Шоп")
async def shop(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    for p in PRODUCTS:
        # Добавляем эмодзи для детей
        emoji = "🍓" if "Strawberry" in p["name"] else "🐱" if "Meowl" in p["name"] else "🚽"
        kb.add(InlineKeyboardButton(f"{emoji} {p['name']} — {p['price']}⭐", callback_data=f"buy_{p['name']}"))
    await message.answer("Выбери брейнрот для покупки:", reply_markup=kb)

# Подтверждение покупки
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def confirm_purchase(call: types.CallbackQuery):
    product_name = call.data[4:]
    product = next((p for p in PRODUCTS if p["name"] == product_name), None)
    if not product:
        await call.message.answer("❌ Товар не найден")
        return
    
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Купить", callback_data=f"pay_{product_name}"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel")
    )
    await call.message.answer(f"Ты точно хочешь купить {product_name} за {product['price']}⭐?", reply_markup=kb)

# Отмена
@dp.callback_query_handler(lambda c: c.data == "cancel")
async def cancel_purchase(call: types.CallbackQuery):
    await call.message.answer("❌ Покупка отменена!")

# Оплата
@dp.callback_query_handler(lambda c: c.data.startswith("pay_"))
async def pay_product(call: types.CallbackQuery):
    product_name = call.data[4:]
    product = next((p for p in PRODUCTS if p["name"] == product_name), None)
    if not product:
        await call.message.answer("❌ Товар не найден")
        return
    
    prices = [LabeledPrice(label=product_name, amount=int(product["price"]*100))]
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=product_name,
        description=product['desc'],
        payload=product_name,
        provider_token="",  # Telegram Stars
        currency=CURRENCY,
        prices=prices
    )

# Предварительный чек
@dp.pre_checkout_query_handler(lambda q: True)
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

# Успешная оплата
@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def got_payment(message: types.Message):
    user_id = str(message.from_user.id)
    item_name = message.successful_payment.invoice_payload
    DB["users"][user_id]["balance"] += int(message.successful_payment.total_amount / 100)
    DB["users"][user_id]["purchases"].append(item_name)
    save_db()
    await message.answer(f"✅ Оплата прошла! Ты купил {item_name} ⭐")

# Админка
@dp.message_handler(lambda m: m.text == "👑 Админка" and m.from_user.id in ADMINS)
async def admin_panel(message: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Выдать ⭐", "📢 Рассылка", "⬅ Назад")
    await message.answer("👑 Админка", reply_markup=kb)

# Запуск
async def main():
    await dp.start_polling()

asyncio.run(main())
