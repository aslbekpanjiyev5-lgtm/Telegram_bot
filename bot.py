import asyncio
import logging
import random
import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔥 FAKE SERVER (Render uchun)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_server).start()

# 🔐 TOKEN
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

CHANNEL = "@starflow_premium"
ADMIN_ID = 6019703915  # sizning ID

participants = set()

# 💾 DATABASE
def save_users():
    with open("users.json", "w") as f:
        json.dump(list(participants), f)

def load_users():
    global participants
    try:
        with open("users.json", "r") as f:
            participants = set(json.load(f))
    except:
        participants = set()

# 📢 OBUNA TEKSHIRISH
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except:
        return False

# 📋 MENU
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎁 Tanlovga qo‘shilish")],
        [KeyboardButton(text="📊 Ishtirokchilar soni")],
        [KeyboardButton(text="🏆 G‘olibni aniqlash")]
    ],
    resize_keyboard=True
)

# 🚀 START
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("⭐ Giveaway botga xush kelibsiz!", reply_markup=menu)

# 🎁 JOIN
@dp.message(lambda message: message.text == "🎁 Tanlovga qo‘shilish")
async def join(message: types.Message):
    user_id = message.from_user.id

    if not await check_sub(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Obuna bo‘lish", url="https://t.me/starflow_premium")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")]
        ])
        await message.answer("❌ Avval kanalga obuna bo‘ling:", reply_markup=kb)
        return

    if user_id not in participants:
        participants.add(user_id)
        save_users()
        await message.answer("Siz tanlovga qo‘shildingiz ✅")
    else:
        await message.answer("Siz allaqachon qo‘shilgansiz 😄")

# 📊 COUNT
@dp.message(lambda message: message.text == "📊 Ishtirokchilar soni")
async def count_users(message: types.Message):
    await message.answer(f"👥 Jami: {len(participants)} ta ishtirokchi")

# 🏆 WINNER (ADMIN)
@dp.message(lambda message: message.text == "🏆 G‘olibni aniqlash")
async def winner(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz admin emassiz")
        return

    if participants:
        win = random.choice(list(participants))
        user = await bot.get_chat(win)
        name = user.full_name
        await message.answer(f"🏆 G‘olib: {name}")
    else:
        await message.answer("Ishtirokchilar yo‘q ❌")

# 🔘 CHECK BUTTON
@dp.callback_query(lambda c: c.data == "check_sub")
async def check_button(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if await check_sub(user_id):
        if user_id not in participants:
            participants.add(user_id)
            save_users()
        await callback.message.answer("Siz tanlovga qo‘shildingiz ✅")
    else:
        await callback.message.answer("❌ Hali obuna bo‘lmadingiz!")

# ▶️ MAIN
async def main():
    logging.basicConfig(level=logging.INFO)
    load_users()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
