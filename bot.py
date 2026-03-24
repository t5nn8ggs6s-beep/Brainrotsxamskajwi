import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
import config  # твой файл с BOT_TOKEN, CHANNEL_ID, ADMINS

# --- Инициализация ---
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# --- Загрузка продуктов ---
with open("products.json", "r", encoding="utf-8") as f:
    products = json.load(f)

# --- Загрузка базы пользователей ---
try:
    with open("database.json", "r", encoding="utf-8") as f:
        db = json.load(f)
except FileNotFoundError:
    db = {"users": {}, "purchases": {}}

# --- Сохраняем базу ---
def save_db():
    with open("database.json", "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

# --- Проверка подписки на канал ---
async def is_subscribed(user_id: int):
    try:
        member = await bot.get_chat_member(config.CHANNEL_ID, user_id)
        return member.status != "left"
    except:
        return False

# --- Клавиатура с продуктами ---
def products_keyboard():
    buttons = [
        [InlineKeyboardButton(
            text=f"{p['name']} — {p['price']}",
            callback_data=f"buy_{p['id']}"
        )]
        for p in products
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

# --- Команда /start ---
@dp.message(Command(commands=["start"]))
async def start(message: types.Message):
    user_id = message.from_user.id

    # Проверка подписки
    if not await is_subscribed(user_id):
        await message.answer(
            f"Пожалуйста, подпишись на канал, чтобы пользоваться магазином: {config.CHANNEL_ID}"
        )
        return

    # Добавление пользователя в базу
    if str(user_id) not in db["users"]:
        db["users"][str(user_id)] = {"stars": 0}
        save_db()

    await message.answer(
        "Привет! Добро пожаловать в Happy Shop 🛍️\nВыбирай своего продукта:",
        reply_markup=products_keyboard()
    )

# --- Обработка покупки (callback) ---
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_product(query: types.CallbackQuery):
    user_id = str(query.from_user.id)
    product_id = query.data.split("_")[1]

    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        await query.message.answer("Ошибка: продукт не найден!")
        return

    user = db["users"].get(user_id)
    if user["stars"] < product["price"]:
        await query.answer("Недостаточно звёзд 🌟", show_alert=True)
        return

    # Списание звёзд и добавление покупки
    user["stars"] -= product["price"]
    db["purchases"].setdefault(user_id, []).append(product_id)
    save_db()

    await query.answer(f"Вы успешно купили {product['name']} 🎉", show_alert=True)

# --- Админка ---
@dp.message(Command(commands=["admin"]))
async def admin_panel(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        await message.answer("Доступ запрещён 🚫")
        return

    await message.answer("Привет, админ! Здесь можно добавить звёзды пользователям.")

# --- Запуск бота ---
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
